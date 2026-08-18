# csss-site-backend

The backend & REST API for the CSSS website. Anything the website frontend does that stores or retrieves information goes through this api. The services this website provides are the following:
- authentication
- (pending) information about executives
- (pending) personalized exams from our bank
- (pending) and more!

## Local Development

See [the csss-backend wiki](https://github.com/CSSS/csss-site-backend/wiki/1.-Local-Setup) for details on how to run the REST API locally on your own machine.

If you're planning to read through the source code, please check out this project's [naming conventions](https://github.com/CSSS/csss-site-backend/wiki/Style-Guide#naming-conventions).

### Quickstart

1. Install [Python 3.13](https://www.python.org/downloads/), [git](https://git-scm.com/install/), and (optionally) [Docker](https://www.docker.com/get-started/)
2. Clone this repository
3. Create and activate a virtual environment for this project. This has been tested with `pip` and `uv`
4. Install developer dependencies
```bash
# Install main dependencies
pip install .        # or: uv sync

# Install with dev dependencies
pip install ".[dev]" # or: uv sync --extra dev

# Install with test dependencies
pip install ".[test]" # or: uv sync --extra test

# Install with all dependencies
pip install ".[dev, test]" # or: uv sync --all-extras
```

5. Follow the database setup instructions on the [wiki](https://github.com/CSSS/csss-site-backend/wiki/1.-Local-Setup#database-setup). The recommended way is to do it through Docker, but both should work.
6. You will need to set the following environment variables set
```bash
DB_PORT=5444 # If you're using Docker
ENVIRONMENT=dev # Set this to `test` if you want to use the test database instead
```
You can also create a `.env` file and set those in there. See `.env.example` for more information.

## Environment Variables

The table below indicates what environment variables we support.
Bolded variables are required or else the server won't start.


| In `.env`           | Python settings key | Type/Options          | Default                                  | Description                                                         |
|---------------------|---------------------|-----------------------|------------------------------------------|---------------------------------------------------------------------|
| **ENVIRONMENT**     | environment         | `dev`, `prod`, `test` | `dev`                                    | Determines some configuration settings on boot up.                  |
| **COOKIE_SECURE**   | cookie_secure       | boolean               | `false`                                  | True if https is required, false otherwise.                         |
| **MEDIA_ROOT**      | media_root          | Path                  | `/srv/csss/media`                        | The directory media file uploads will be placed into.               |
| **MEDIA_BASE_URL**  | media_base_url      | string                | `/media`                                 | The base URL clients use to retrieve media.                         |
| ALLOWED_ORIGINS     | allowed_origins     | JSON string array     | `["http://localhost:8080"]`              | The browser origins that can send API requests.                     |
| AUTH_REDIRECTS      | auth_redirects      | JSON string array     | `["http://localhost:8080"]`              | The browser origins that authentication can redirect to.            |
| AUTH_URL            | auth_url            | string                | `https://cas.sfu.ca/cas/serviceValidate` | The authentication service URL.                                     |
| DB_PORT             | db_port             | 0 - 65535             | `5444`                                   | The port the database is reachable at, set this if working locally. |
| TRANSLINK_API_KEY   | translink_api_key   | string                |                                          | The API key used to retrieve real-time TransLink schedule data.     |
| COOKIE_DOMAIN       | cookie_domain       | string                |                                          | Domain value of the cookie.                                         |
| KIOSK_SECRET        | kiosk_secret        | string                |                                          | The key to use to validate Kiosk requests.                          |


The `ENVIRONMENT` dictates the following behaviour:

| Value  | Database Used | Documentation URL (`/docs`) | Authorization Checks |
|--------|---------------|-----------------------------|----------------------|
| `dev`  | main          | Enabled                     | Disabled             |
| `test` | test          | Enabled                     | Enabled              |
| `prod` | main          | Disabled                    | Enabled              |

- The test suite always uses the `test` environment.
- Alembic always runs its migrations on the main database.

## Important Directories

- `config/` configuration files for the server machine
- `src/`
    - `alembic` database migrations
    - `auth/` controlling authentication and sessions
    - `candidates/` management of those who run in large elections
    - `elections/` mangement of current elections & past elections
    - `event/` management of events
    - `nominees/` management of nominees to large elections
    - `officers/` management of officer information and terms
    - `translink/` management of TransLink REST API
- `test/` unit and integration tests

## Developer Tools

We use `ruff` as our linter, which you can run with `ruff check --fix`. If you use a different version, it may be inconsistent with our CI checks.
We use `pyright/basedpyright` for typechecking. Language services have been left enabled and will be changed if it becomes an issue.
