import trip, datetime

class triplist(object):
    def __init__(self, firsttrip, numberoftrips=0, relocationsoffered=0,\
                 relocationsaccepted=0):
        self.totalidle = datetime.timedelta(seconds=0)
        self.totalrental = datetime.timedelta(seconds=0)
        self.numberoftrips = numberoftrips
        self.trips = list()
        self.addtrip(firsttrip)
        self.relocationsoffered = relocationsoffered
        self.relocationsaccepted = relocationsaccepted

    def addtrip(self, tta):
        self.totalidle += tta.idle_time
        self.totalrental += tta.rental_time
        self.numberoftrips += 1
        tempstart = tta.start
        tempend = tta.end
        temptime_start = ' '
        temptime_start = tta.time_start.isoformat(' ')
        temptime_end = ' '
        temptime_end = tta.time_end.isoformat(' ')
        tempidle_time = datetime.timedelta(seconds=tta.idle_time.total_seconds())
        tempvin = tta.vin
        newtrip = trip.trip(tempstart, tempend, temptime_start, temptime_end, tempidle_time, tta.model, tempvin)
        newtrip.UIN = tta.UIN
        self.trips.append(newtrip)
        return 0

    def refresh(self):
        self.totalidle = datetime.timedelta(seconds=0)
        for i in self.trips:
            self.totalidle += i.idle_time
        self.totalrental = datetime.timedelta(seconds=0)
        for i in self.trips:
            self.totalrental += i.rental_time
        self.numberoftrips = 0
        for i in self.trips:
            self.numberoftrips += 1
        return 0
