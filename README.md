# Documents management service

The service is used for documents generation from templates (supports PDF, HTML and DOCX formats)
and for signing generated documents using [DocuSign](https://www.docusign.com/).

The project is developed around two libraries: [FastAPI](https://fastapi.tiangolo.com/) and
[Python dependency injector](https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html).


# Table of Contents

* [Prerequisites before developing](#prerequisites-before-developing)
* [Developing](#developing)
* [Tests](#tests)
* [Environment variables](#environment-variables)
* [Services](#services)
* [Code review, releases and committing](#code-review-releases-and-committing)
<!-- TOC -->


# Prerequisites before developing

Before you start development of the feature in project you should set up account and application
in DocuSign https://developers.docusign.com/. After signing and logging to DocuSign,
you [should generate JWT token](https://developers.docusign.com/platform/auth/jwt/jwt-get-token/).

Also, it would be better, if you [install](https://github.com/pyenv/pyenv-installer#install)
pyenv - Python version management.


# Developing
1. Firstly, you [should install](https://python-poetry.org/docs/#installation) poetry -
Python packaging and dependency management. If you use Linux based system you can use this shell script:
   ```shell
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Secondly, Go to project with file pyproject.toml, create local environment and start it using the script below:
   ```shell
   poetry shell
   ```

   You have to use this script before starting application or when you need to update dependencies.
3. After that you can install all dependencies, including development dependencies:
    ```shell
    poetry install
    ```

4. Install pre-commit to set up the git hook scripts:
   ```shell
   pre-commit install
   ```

   Pre-commit will run on every commit automatically, and you must fix issues before committing changes.
5. Starting services which are needed for development [services](#services):
   ```shell
   make tests-up
   ```

6. Go through the link http://localhost:9000, enter the username and password (you can find it in docker-compose.yml file),
   create a test bucket with name 'testbucket', create a folder with name 'templates' and upload files from directory
   minio/data to folder 'templates'.

7. Run script the below for creating tables for working with DynamoDB locally:
   ```shell
   make create-tables
   ```
   You can install
   [NoSQL Workbench for DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.html) for
   viewing and working with tables locally.

   If you want to update table or add a new one to work with DynamoDB, you should update script
   [local_db_migration.py](scripts/local_db_migration.py)

8. Create file with name '.env', copy content of the file with name '.env.example' and paste it to file '.env'. After that
   you must fill in the values (`DOCU_SIGN__CLIENT_ID`, `DOCU_SIGN__PRIVATE_KEY_ENCODED`, `DOCU_SIGN__ACCOUNT_ID`,
   `DOCU_SIGN__IMPERSONATED_USER_ID`) if you are going to work with DocuSign. All list of environment variables and why
   they are needed you can check in the [paragraph](#environment-variables).

9. [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) in your local
   machine and configure account. If you don't have account, you should go to AWS Administrator or Team Manager.
   Strongly recommend using the second versions of AWS CLI.

10. After all steps you can start your application locally using one of these scripts:
    ```shell
    export AWS_DEFAULT_REGION='us-east-1' && uvicorn app.main:app --host localhost --port 8000
    ```
    ```shell
    make run
    ```
    You must specify `AWS_DEFAULT_REGION` variable when start your application.


# Tests

The project uses pytest for running tests. The directory [tests](tests) contains integration tests and separate tests for
testings service. The directory [tests](tests) has separate module which display the project modules.

If you want to run tests you should run these scripts:
```shell
export ENV_FILE_NAME='.env.tests' && \
export AWS_DEFAULT_REGION='us-east-1' && \
poetry run pytest --cov=app --cov-report=term:skip-covered --cov-report=html:coverage --cov-fail-under=90 ./tests
```
```shell
make tests-run
```
Tests coverage should be above 90% for the whole project. After the running of the tests with coverage report,
you can check result of coverage [in this file](coverage/index.html)


# Linter

The project uses [wemake-python-styleguide](https://wemake-python-styleguide.readthedocs.io/en/latest/) library (linter),
which based on [flake8](https://flake8.pycqa.org/en/latest/), and [mypy](https://mypy.readthedocs.io/en/stable/)
(static type checker). You can configure linter settings in [setup.cfg](setup.cfg) file, but, firstly, discuss with
your teammates. Static checker is run automatically before committing, and you can run statick checker using these scripts:
```shell
make static-check # flake8 and mypy
```
```shell
flake8 .
```
```shell
mypy .
```


# Environment variables

This paragraph contain table with variables and description why it needed

| Name of variable                                | Description of variable                                                                      | Default                | Production          |
|-------------------------------------------------|:---------------------------------------------------------------------------------------------|:-----------------------|:--------------------|
| `GOTENBERG__URL`                                | URL to the Gotenberg                                                                         | http://localhost:3000  | Specified by DevOps |
| `AWS_SETTINGS__ACCESS_KEY_ID`                   | Access key for Minio                                                                         | minioadmin             | Empty               |
| `AWS_SETTINGS__SECRET_ACCESS_KEY`               | Secret access key for Minio                                                                  | IZts0i8E9E2slIkv       | Empty               |
| `STORAGE__ENDPOINT_URL`                         | URL for Minio                                                                                | http://localhost:9000/ | Not used            |
| `STORAGE__MAIN_BUCKET_NAME`                     | Bucket, where service working with files                                                     | testbucket             | Specified by DevOps |
| `DYNAMO_STORAGE__ENDPOINT_URL`                  | URL for Localstack                                                                           | http://localhost:4566/ | Not used            |
| `DYNAMO_STORAGE__DOCUMENTS_TABLE_NAME`          | Table with request information                                                               | Documents              | Specified by DevOps |
| `DYNAMO_STORAGE__ENVELOPES_TABLE_NAME`          | Table with envelope information                                                              | Envelopes              | Specified by DevOps |
| `DYNAMO_STORAGE__ENVELOPE_CALLBACKS_TABLE_NAME` | Table with envelope callbacks information                                                    | EnvelopeCallbacks      | Specified by DevOps |
| `DOCU_SIGN__CLIENT_ID`                          | Integration Key                                                                              | Empty                  | Specified by DevOps |
| `DOCU_SIGN__PRIVATE_KEY_ENCODED`                | Base64 encoded private key generated using [DocuSign API](#prerequisites-before-developing). | Empty                  | Specified by DevOps |
| `DOCU_SIGN__ACCOUNT_ID`                         | API Account ID                                                                               | Empty                  | Specified by DevOps |
| `DOCU_SIGN__IMPERSONATED_USER_ID`               | User ID                                                                                      | Empty                  | Specified by DevOps |
| `DOCU_SIGN__WEBHOOK_URL`                        | Full URL to our endpoint which process webhook data (api/v1/esign/webhook)                   | Empty                  | Specified by DevOps |


# Services

| Service name          | Address               | Docs                                                             | Used in production |
|-----------------------|-----------------------|:-----------------------------------------------------------------|--------------------|
| Gotenberg             | http://localhost:3000 | https://gotenberg.dev/docs/about                                 | Yes                |
| Minio                 | http://localhost:9000 | https://min.io/docs/minio/container/operations/installation.html | No                 |
| Localstack (DynamoDB) | http://localhost:4566 | https://docs.localstack.cloud/user-guide/aws/feature-coverage/   | No                 |


# Code review, releases and committing

Code review in the project is required.
To use or create semantic release - every commit must have one of the available prefixes (could be customized here):

* (0.0.x) - increments last digit. Prefixes: **docs**, **bug**, **fix**, **refactor**;
* (0.x.0) - increments middle digit. Prefixes: **feature**;
* (x.0.0) - increments first digit. Prefixes: **release**;

Examples of commit messages:
- `git commit -m "bugfix: PRIME-123 | bug fixed"`;
- `git commit -m "bugfix(PRIME-123): bug fixed"`;
- `git commit -m "feature: PRIME-123 | bug fixed"`;
