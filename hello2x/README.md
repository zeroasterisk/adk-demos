# ADK Hello World x2

## First Time Setup

Read docs here: [ADK Quickstart](https://google.github.io/adk-docs/get-started/quickstart/#env)

```sh
cd hello2x
python -m venv .adk_venv
source .adk_venv/bin/activate
pip install google-adk
pip install -r requirements.txt
```

Setup `.env` file inside each agent folder

```sh
cp hello1/.env-template hello1/.env
edit hello1/.env
cp hello1/.env hello2/.env
```

It should look something like:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT="myproject"
GOOGLE_CLOUD_LOCATION="us-central1"
```

And don't forget to login to Google Cloud.

```bash
gcloud auth login
```

## Usage


