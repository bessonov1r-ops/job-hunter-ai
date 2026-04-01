class Job:
    def __init__(self, title, company, city, url, source, description=""):
        self.title = title
        self.company = company
        self.city = city
        self.url = url
        self.source = source
        self.description = description