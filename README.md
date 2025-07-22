# geep-shared-otel-logger-python

This is a shared python module currently only containing an importable module for python to do Opentelemetry logging. For reasons discussed below, future shared python code should also go into this module.

Looking for the python development guide? - see [here](docs/geep_python_developers_guide.md)

# Table of contents

1. [Setting up a shared repo](#setting-up-a-shared-repo)
2. [Adding the logger to a service](#adding-the-logger-to-a-service)
3. [Using the logger](#using-the-logger)
4. [Using a local open telemetry collector](#using-a-local-collector)
5. [Using traces](#using-traces)
6. [Generating Type Stubs](#generating-type-stubs)
7. [How does all this stuff work, anyway?](#how-does-all-this-stuff-work-anyway)

## Setting up a shared repo <a name="repo_setup"></a>

### Setting up a deploy key for a shared module accessed from a private repo.

The steps below have been done and don't need to be repeated. However I have included them for future reference in case we want to use this method for another shared private repo. For typescript, we used git packages but these don't support pypi.

As per instructions [here](~https://gist.github.com/zhujunsan/a0becf82ade50ed06115~),

a. Create a new key locally. Make sure you leave the passphrase blank for the key. Note the `-C "{ssh_repo_url}"` is important as it is used by the github action we use.

```bash
ssh-keygen -t rsa -b 4096 -C "git@github.com:britishcouncil/geep-shared-otel-logger-python.git" -f $HOME/.ssh/id_rsa_python_logging
```

b. View / Copy your public key

```bash
cat $HOME/.shh/id_rsa_python_logging.pub
```

c. In github, for this repo, Create a deploy key by going to

```
https://github.com/britishcouncil/{repo}/settings/keys
```

Ensure it is read only.

## Adding the logger to a service

Follow these steps to configure a service to use this module.

### 1. Add the private key to the service repo

For the repo for your service, add the private key to the repository-level secrets.

If you created it yourself, you can get it via

```bash
cat $HOME/.ssh/{name of id_rsa file for private key}
```

Or, to use the existing private key for this service, go to AWS Secrets manager and look for `SHARED_PYTHON_SSH_PRIVATE_KEY`.

Then copy and add the keyas a _Repository Secret_ (you can use any name but, to follow these examples, use `SHARED_PYTHON_SSH_PRIVATE_KEY`). (This could be an org-level secret but we are following principle of least privilege)

```
https://github.com/britishcouncil/{repo}/settings/keys
```

### 2. Install the module

Normally this will be

```bash
poetry add git+ssh://git@github.com/britishcouncil/geep-shared-otel-logger-python.git
```

You can also use this syntax to install from a branch of this module for testing purposes.

```bash
poetry add git+ssh://git@github.com/britishcouncil/geep-shared-otel-logger-python.git#GP2-664-Shared-logger-module
```

### 3. Update github actions workflows

The CI needs to be updated to use the new key. Your update will depend on what your workflow is doing. Before you do this, you will need to add the key to your repo.

- The private key to access this repo can be found in AWS secrets manager in non-prod: `geep-shared-python-ssh-private-key`
- Use this to create a new repository-level secret for the repoin github: Settings/Secrets and variables/Actions/Repository Secrets. Call the key `SHARED_PYTHON_SSH_PRIVATE_KEY` and paste in the private key you just got from aws.

### 3.1a. Workflow doesn't do docker build, e.g. some CI workflows

Add these two steps after the initial checkout step.

```yaml
- name: Check SSH installed
  run: |
    which ssh || (apt-get update && apt-get install -y ssh)

- name: Set up SSH key for shared python repo access
  uses: britishcouncil/geep-github-actions/ssh-agent@main
  with:
    ssh-private-key: ${{ secrets.SHARED_PYTHON_SSH_PRIVATE_KEY }}
```

### 3.1b. Workflow does docker build using build-and-push action

e.g. This action: britishcouncil/geep-github-actions/build-push-action@main

As before, add this after the initial checkout step

```yaml
- name: Set up SSH key for shared python repo access
  uses: britishcouncil/geep-github-actions/ssh-agent@main
  with:
    ssh-private-key: ${{ secrets.SHARED_PYTHON_SSH_PRIVATE_KEY }}
```

This is for docker builds during the workflow which don't use `docker-compose`. Add this to the build and push

```yaml
ssh: default=${{ env.SSH_AUTH_SOCK }}
```

e.g.

```yaml
uses: britishcouncil/geep-github-actions/build-push-action@main
with:
  context: .
  push: false
  load: true
  cache-from: type=gha
  cache-to: type=gha,mode=max
  tags: ${{env.ECR_REGISTRY}}/${{env.ECR_REPOSITORY}}:current
  ssh: |
    default=${{ env.SSH_AUTH_SOCK }}
```

### 3.1c. Workflow uses docker compose

No changes are needed in the workflow, but changes are needed in the Dockerfile and docker-compose file for it to work.

### 4. Update Dockerfile

(See the dialogue service for examples)

1. Add `openssh` to system dependencies

```yaml
# Install system dependencies
RUN apk update && apk add build-base curl gcc libc-dev libffi-dev g++ linux-headers openssh
```

2. On the next line add this code to cache the github.com public key without prompting you to accept it.

```yaml
# add host public key for github (for logging repo) to known hosts
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
```

3. In the `RUN poetry install` or `RUN pip` line, add an extra parameter `--mount-type=ssh`. This tells docker to use a read-only socket to the host's ssh agent for that line only, and sets up the env var SSH_AUTH_SOCK.

`RUN --mount=type=ssh poetry install --no-root --without dev --no-interaction --no-ansi`

### 5. Update Docker Compose

In the `docker-compose` file, for any application which needs to access the host ssh agent, add this `ssh: [default]` section under `build` ([ref](~https://github.com/compose-spec/compose-spec/pull/234~)). This will work in CI and locally as long as you can access github normally.

```yaml
api:
  build:
    context: .
    ssh: [default]
```

When running docker-compose with the app as well, the app needs to use internal routing within the docker network to contact the otel collector container.

The `.env.docker` file is used in docker compose for env vars specific to this configuration. Add this line to that file.

`OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://otelcol:4318/v1/logs`

### 6. Running docker locally

To run docker locally _without_ using docker compose, use `docker build --ssh default .` to define that ssh forwarding is allowed for this build. This doesn't need the private deploy key to work - it'll use the normal key you use to access github.

## Using the logger

Once the logger is imported, in python logging is simply a case of fetching a logger using

```python
from geep_shared_otel_logger_python import log_config

logger = log_config.get_logger_and_add_handler(
    "geep-database-service", "database.db_crud"
)
```

Where `geep-database-service` should be replaced with your service name and `database.db_crud` is the name for this particular logger (usually the full name of the calling module).

### Adding our logger to Uvicorn

Our FastAPI applications use Uvicorn, an Asynchronous Gateway Interface (ASGI) web server implementation for Python. When Uvicorn starts up it creates a logger and resets other loggers and handlers. Uvicorn uses three loggers "default", "access" and "error". You must add a handler to send the Uvicorn logs to the OpenSearch collector. You can add a handler in the log_config option of the Uvicorn run function.

Developers can use the uvicorn_config function from this module to add our recommended configuration. See the code example below for how to do this:

```python
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config=log_config.get_uvicorn_log_config(),
        log_level=log_config.get_log_level_name_lower(),
    )
```

## Using a local open telemetry collector

There are several ways to run the otel collector

### Docker Compose

In each python service we update, we're currently adding a local collector. In due course we'll probably centralise that code, but until that happens it's worth adding the collector locally into `docker-compose` so developers can run and test logging locally.

To do this, create a file called `otel-collector-config.yml` in the project root. There's an example file in the root of this repo.

Then, add the otel container config to your `docker-compose.yml`. Again, there's an example in this the root of this repo.

### Use the executable

## Using Tracings

In your service, import the tracing utilities and initialize the tracer:

```python
from geep_shared_otel_logger_python import tracing_utils

tracer = tracing_utils.create_tracer("my-service")
```

Tracing is much better with instrumentation, so you should also import appropriate instrumentation libraries:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Instrument the FastAPI application
FastAPIInstrumentor.instrument_app(app)

# Add trace id to logs
LoggingInstrumentor(set_logging_format=True)
```

Finally, the OTLP tracing exporter reads the tracing URL from an environment variable, so set that in your environment

```
#.env

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://jaegercol:4318/v1/traces
```

## Using a local trace collector

The below is a docker-compose service for a trace collector. If you port forward to open search in dev and set your environment variable as suggested above, jaeger will export traces to OpenSearch.

```
  jaegercol:
    image: jaegertracing/jaeger-collector:latest
    ports:
      - "4319:4318"
    restart: unless-stopped
    profiles: [dev]
    environment:
      - SPAN_STORAGE_TYPE=opensearch
      - ES_TAGS_AS_FIELDS_ALL=true
    command: [
      "--es.server-urls=http://host.docker.internal:5602",
    ]
```

## Useful Envs

```
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT= #the logs collector
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT= #the trace collector url
OTEL_PYTHON_LOG_CORRELATION= #tells logging instrumentor to inject trace into logs
OTEL_PYTHON_EXCLUDED_URLS= #exclude urls from being collected (this is set in helm common for health)
ENVIRONMENT= #Set environment local to disable otel handlers in local
```

## Generating Type Stubs <a name="generating-type-stubs"></a>

This repository uses pyright stub files (`.pyi`) to provide type hints. When adding new modules or making significant changes to existing ones, you'll need to regenerate the stub files.

### Generating Stubs with Pyright

To generate stub files for a module:

```bash
# Generate stubs for a specific module
poetry run pyright --createstub geep_shared_python.schemas

# Or for a specific submodule
poetry run pyright --createstub geep_shared_python.schemas.shared_schemas
```

### Handling Generated Stubs

By default, pyright places generated stubs in a separate `typings` folder instead of alongside the Python modules. In this repository, we keep stub files next to their Python modules, so you'll need to:

1. Generate the stubs as shown above
2. Manually copy the generated `.pyi` files from the `typings` folder to their proper location

For example:

```bash
# Generate stubs for a utility module
poetry run pyright --createstub geep_shared_python.utils.text_utils

# Move the stub file to be next to the Python module
mv typings/geep_shared_python/utils/text_utils.pyi geep_shared_python/utils/
```

### Important Notes

- Avoid reformatting stub files with code formatters or linters, as this can break them
- Only regenerate stubs when necessary (e.g., after adding new classes or changing function signatures)

## How does all this stuff work, anyway?

For an explanation of the design of the logger code go to [this confluence page](https://britishcouncil.atlassian.net.mcas.ms/wiki/spaces/GEEP/pages/306413569/Otel+Logging+Tracing+in+Python+POC).

The challenge here was to access the private repo using a private key without caching the key anywhere in the process. This is a risk with docker as if the key is copied into the filesystem it can be cached in a layer or appear in the docker history.

### Workflow-level SSH Agent

First, the `ssh-agent` steps runs in the CI. (See [here](https://github.com/marketplace/actions/webfactory-ssh-agent) for documentation)

This does three things:

- starts the ssh-agent
- exports the `$SSH_AUTH_SOCK` env var and
- loads the `secrets.SHARED_PYTHON_SSH_PRIVATE_KEY` into the agent

As long as ssh is installed on the host, then the repo will be able to be fetched.

### Docker and docker compose

`docker compose` and `docker build` both need to be configured to forward any ssh requests out to the agent upon which docker is being run, so it can provide back the key in-memory. This is achieved by passing the socket through to the docker container. The container is then configured to use the socket for ssh auth so it fetches the correct key from the host.

First the docker compose needs to pass the socket through to docker build. This line is a recent edition to docker compose which does [that](https://github.com/compose-spec/compose-spec/pull/234):

`ssh: [default]`

This adds `--mount=type=ssh` to the docker build.

Then in the `Dockerfile`, we need to avoid the message which you get when you first connect to a host with ssh, since that message requires the user to explicitly accept the key.

```yaml
# add host public key for github (for logging repo) to known hosts
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
```

And then in the `poetry install` in the Dockerfile, the use of `--mount=type=ssh` then uses the socket to contact the enclosing host `ssh-agent` to access right private key. eg. See [here](https://medium.com/@tonistiigi/build-secrets-and-ssh-forwarding-in-docker-18-09-ae8161d066) and [here](https://github.com/moby/buildkit/blob/1c55173219144bf4db6e47b80cb33566658bd775/frontend/dockerfile/docs/reference.md?plain=1#L678).

```yaml
https://medium.com/@tonistiigi/build-secrets-and-ssh-forwarding-in-docker-18-09-ae8161d066
```
# geep-shared-python-main
