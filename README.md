# csss-site-backend

The backend & REST API for the CSSS website. Anything the website frontend does that stores or retrieves information goes through this api. The services this website provides are the following:
- authentication
- (pending) information about executives
- (pending) personalized exams from our bank
- (pending) and more!

## Local Development

See [the csss-backend wiki](https://github.com/CSSS/csss-site-backend/wiki/1.-Local-Setup) for details on how to run the REST API locally on your own machine.

If you're planning to read through the source code, please check out this project's [naming conventions](https://github.com/CSSS/csss-site-backend/wiki/Style-Guide#naming-conventions).

## Important Directories

- `config/` configuration files for the server machine
- `src/`
    - `alembic` for database migrations
    - `access/` for controlling officer access to the google drive, bitwarden, and github. TODO: discord as well?
    - `blog/` for running an editable csss-blog
    - `dashboard/` for controlling the server, website, jobs, and access to services & stuff.
    - `elections/` for the mangement of current elections & past elections
    - `jobs/` for cronjobs that run regularly on the server
    - `misc/` for anything that can't be easily categorized or is very small
    - `officers/` for officer contact information + photos
- `test/` for html pages which interact with the backend's local api

## Linter

We use `ruff 0.6.9` as our linter, which you can run with `ruff check --fix`. If you use a different version, it may be inconsistent with our CI checks.
