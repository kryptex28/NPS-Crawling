# NPS-Crawling

Important: For more information, have a look at the confluence of project.

## Build the project as package
```shell
pip install -e .
```

## Run the project
- Crawl process 
```shell
nps-crawling crawl
```

- Process process
```shell
nps-crawling process
```

- Classify process
```shell
nps-crawling classify
```

- Display process (currently no functionality)
```shell
nps-crawling display
```

## Crawl Settings
Settings for the crawler can be found in [src/nps_crawling/crawler/settings.py](https://github.com/kryptex28/NPS-Crawling/blob/main/src/nps_crawling/crawler/settings.py). To limit the amout of queries to be crawled, change the parameter `SEC_QUERY_LIMIT_COUNT`. 


## Linting
```shell
tox -e lint
```
and
```shell
tox -e lint -- --fix
```