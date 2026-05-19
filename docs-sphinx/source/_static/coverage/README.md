# Coverage reports

This directory is populated automatically during the CI → Docs pipeline.

Each sub-directory (`auth-service/`, `inventory-service/`, `transaction-service/`,
`agentic-service/`) contains the full `pytest-cov` HTML report for that service,
injected by the `sphinx-docs.yml` workflow step "Inject coverage reports into Sphinx
_static" immediately before `make html` runs.

**Local builds**: these reports are not present when building Sphinx locally.
The links in `testing.md` will resolve to a 404 in local builds — this is expected.
To get the reports locally, run the test suite for the service you need:

```bash
cd backend/<service>
pytest --cov=app --cov-report=html:coverage-html
# then open backend/<service>/coverage-html/index.html
```
