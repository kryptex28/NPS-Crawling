import json

class SaveToJSONPipeline:
    def open_spider(self, spider):
        self.file = open('nps_filings.json', 'w')
        self.file.write('[')

    def close_spider(self, spider):
        self.file.write(']')
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + ",\n"
        self.file.write(line)
        return item
