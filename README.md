# NPS-Crawling

## Build 
### Prerequisites
```sh
pip install tox
pip install uv
```

### Build the project as package
```shell
pip install -e .
```

## Linting
```shell
tox -e lint
```
and
```shell
tox -e lint -- --fix
```