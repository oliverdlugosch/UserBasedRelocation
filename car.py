import database, datetime, trip

class car(object):
    def __init__(self, vin=None, model=None):
        self.vin = vin
        self.model = model
        self.trips = list()
        self.trips = self._getTrips()

    def _getTrips(self):
        trips = list()
        tripPoints = self._getTripPoints()
        # There must be at least 2 trip points for one complete trip
        if len(tripPoints) > 1:
            start = {"lat": tripPoints[0][0], "lon": tripPoints[0][1]}
            start['lat'] = float(start['lat'])
            start['lon'] = float(start['lon'])
            time_start = tripPoints[0][2]
            i3 = 0
            for point in tripPoints[1:]:
                i3 += 1
                end = {"lat": point[0], "lon": point[1]}
                end['lat'] = float(end['lat'])
                end['lon'] = float(end['lon'])
                idle = datetime.datetime.strptime(point[3], "%Y-%m-%d %H:%M:%S.%f") - datetime.datetime.strptime(point[2], "%Y-%m-%d %H:%M:%S.%f")
                # Only append trip if trip doesn't exist yet
                if any(trip.time_start == time_start and trip.time_end == point[2] for trip in self.trips) == False:
                    t = trip.trip(start, end, time_start, point[2], idle, self.model, self.vin)
                    trips.append(t)
                start = end
                time_start = point[3]
        return trips


    def _getTripPoints(self):
        query = "SELECT lat, lon, timestamp as datetime, timestamp_end as datetime FROM %s WHERE vin = '%s' AND timestamp_end IS NOT '' ORDER BY timestamp"% (self.model.location,self.vin[0])
        trip_points = database.selectDataObjects(query, self.model.location)
        return trip_points
