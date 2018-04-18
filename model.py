import datetime, database, car, pickle, csv, random, triplist, tile, haversine, math, scipy
from scipy import stats

class model(object):
    # Initialize an instance of model
    def __init__(self, location=None, numberofruns=None, latdelta=0.0, londelta=0.0):
        self.location = location
        self.numberofruns = numberofruns
        self.x = None
        self.y = None
        self.d = list()
        self.r = list()
        self.firstday = None
        self.lastday = None
        self.cars = list()
        self.tiles = list()
        self.latdelta = latdelta
        self.londelta = londelta
        self.incentive = 0.0 # Minutes to be given to user for conducted relocation
        # Set of parameters to be specified here (not in config.ini):
        # Time window for calculation of estimated idle time (EIT),
        # i.e., time span before and after arrival of trip which trips from
        # training set need to end in to be considered for EIT calculation
        self.timewindowEIT = datetime.timedelta(minutes=30)
        # Radius around end location of trip that trips from training set need
        # to end in to be considered for EIT calculation [in km]
        self.sigmaEIT = 0.5
        # Radius around end location of trip that tile centers need to be in
        # to be considered for tile creation [in km]
        self.sigmaTiles = 0.5
        # Radius around end location of trip that trips from test set need
        # to end in to be considered for relocation trips [in km]
        self.sigmaY = 0.5

    # Run the simulation
    def run(self, threshold, probdistr):

        ###############################
        ### Define paths for output ###
        ###############################

        temppath1 = './_results'
        temppath2 = '/k_'
        temppath3 = [temppath1, temppath2]
        temppath1 = "".join(temppath3)
        temppath3 = [temppath1, str(threshold)]
        temppath3 = "".join(temppath3)
        temppath2 = '.csv'
        temppath1 = [temppath3, temppath2]
        temppath1 = "".join(temppath1)
        pathsingletrips = temppath1
        temppath4 = './_results'
        temppath5 = '/k_summary_'
        temppath6 = [temppath4, temppath5]
        temppath4 = "".join(temppath6)
        temppath6 = [temppath4, str(threshold)]
        temppath6 = "".join(temppath6)
        temppath5 = '.csv'
        temppath4 = [temppath6, temppath5]
        temppath4 = "".join(temppath4)
        pathsummary = temppath4
        temppath1 = './_results'
        temppath2 = '/eloc_'
        temppath3 = [temppath1, temppath2]
        temppath1 = "".join(temppath3)
        temppath3 = [temppath1, str(threshold)]
        temppath3 = "".join(temppath3)
        temppath2 = '.csv'
        temppath1 = [temppath3, temppath2]
        temppath1 = "".join(temppath1)
        pathreloc = temppath1

        #####################################
        ### Open output and write headers ###
        #####################################

        wr5file = open(pathsingletrips, 'w')
        writer5 = csv.writer(wr5file, delimiter=";", lineterminator='\n')
        header5 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'IdleTime', 'RentalTime', 'Vin', 'UIN', 'Trips this day', 'First of day')
        writer5.writerow(header5)
        wr5file.flush()
        wr6file = open(pathsummary, 'w')
        writer6 = csv.writer(wr6file, delimiter=";", lineterminator='\n')
        header6 = ('Number of Trips', 'Total Idle Time', 'Total Rental Time', 'Relocations offered', 'Relocations accepted')
        writer6.writerow(header6)
        wr6file.flush()
        wr7file = open(pathreloc, 'w')
        writer7 = csv.writer(wr7file, delimiter=";", lineterminator='\n')
        header7 = ('UIN arriving trip', 'UIN planned trip', 'UIN relocated trip', 'EIT target tile', 'EIT reloc tile', 'Distance between trip end and Reloc Tile', 'Acceptance probability', 'Old idle time', 'New idle time')
        writer7.writerow(header7)
        wr7file.flush()

        ##################
        ### Simulation ###
        ##################

        # Simulation is structured along the sequence of trips for one particular
        # car on one day - the 'car day'. The baseline 'd' is a random set of these
        # car days picked from the test set. Self.r is the list of actually conducted
        # trips as a result of the simulation, i.e., containing both trips from d and,
        # if relocation occured, other trips.

        self.r = list()
        for itriplist in self.d:

            # Simulation will end once the last of the saved trips and its idle time
            # end on any day after the day of the first trip in the car day.
            # Therefore defining times, days and appending the first trip of the day
            # as conducted.

            today = itriplist.trips[0].time_start
            endofday = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
            currenttime = itriplist.trips[0].time_end + itriplist.trips[0].idle_time
            self.r.append(triplist.triplist(itriplist.trips[0]))
            i = 0

            # Marker that tells if simulation is 'still in d', i.e., no relocation
            # has been conducted on that car day. Once this marker turns to False,
            # i.e. at least one relocation was conducted, the baseline car day will
            # not be used for finding subsequent trips for the car day that is being
            # simulated.

            stillind = True
            while currenttime < endofday:

                # Find destination, arrival time and estimated idle time for arrival
                # tile of current trip

                targettile = self.initiatetiles(self.r[-1].trips[-1])
                targettime = datetime.time(self.r[-1].trips[-1].time_end.hour, \
                                           self.r[-1].trips[-1].time_end.minute,\
                                           self.r[-1].trips[-1].time_end.second)
                targettileEIT = self.getEITfromx(targettile, targettime)
                if targettileEIT is not None:

                    # We have enough data to calculate an EIT for target tile.
                    # Find all tiles that are relevant, i.e., tiles with a sufficiently low
                    # EIT and trips from test set that are eligible as relocation trips

                    relevantEIT = self.getrelevantEIT(self.r[-1].trips[-1], targettile, targettime, targettileEIT, threshold)
                    if relevantEIT is not None:

                        # We have at least one relevant tile.
                        # Find the closest of the relevant tiles for calculation of acceptance probability.

                        offeredRelocation = self.getclosesttile(relevantEIT, self.r[-1].trips[-1], targettile)
                        probability = self.getaccprobability(offeredRelocation, probdistr)
                        self.r[-1].relocationsoffered += 1

                        # We offer a relocation.
                        # Determine if relocation offer is being accepted based on probability.

                        reloc = scipy.stats.rv_discrete(name='relocDist', \
                        values=((0, 1), (1.0 - probability, probability)))  # random generator
                        relocVar = reloc.rvs()
                        if relocVar == 1:

                            # Relocation has been accepted.
                            # Select the picked tile and the relocation trip. 'pickedtrip' contains
                            # the trip that has fulfilled the requirements for the arriving trip. So the trip
                            # that will be added to self.r as the next conducted trip in the simulation is the trip that
                            # followed 'pickedtrip' and therefore has a UIN that is larger by 1.

                            pickedtrip = self.picktrip(relevantEIT, self.r[-1].trips[-1])
                            preAcceptedTrip = pickedtrip[0]
                            for itrip in self.y:
                                if itrip.UIN == preAcceptedTrip.UIN + 1:
                                    acceptedTrip = itrip

                            # The relocation trip is saved as 'acceptedTrip'.
                            # Write the relocation event to output.

                            header7 = (self.r[-1].trips[-1].UIN, self.r[-1].trips[-1].UIN + 1, acceptedTrip.UIN,\
                                       targettileEIT, pickedtrip[1], pickedtrip[2],\
                                       probability, self.r[-1].trips[-1].idle_time.total_seconds()/60.0, preAcceptedTrip.idle_time.total_seconds()/60.0)
                            writer7.writerow(header7)
                            wr7file.flush()

                            # Adjust times of relocation trip, count accepted relocation, add trip to self.r,
                            # update current time and mark that simulation is no longer in d, i.e., at least
                            # one relocation has been conducted.

                            temptime = preAcceptedTrip.idle_time.total_seconds()
                            self.r[-1].trips[-1].idle_time = datetime.timedelta(seconds=temptime)
                            self.r[-1].relocationsaccepted += 1
                            self.r[-1].addtrip(acceptedTrip)
                            self.r[-1].trips[-1].time_start = self.r[-1].trips[-2].time_end + preAcceptedTrip.idle_time
                            self.r[-1].trips[-1].time_end = self.r[-1].trips[-1].time_start + \
                                                           self.r[-1].trips[-1].rental_time
                            currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                            stillind = False
                        else:

                            # Relocation has NOT been accepted.
                            # If simulation is still in d, take the subsequent trip as next trip.

                            if stillind:
                                self.r[-1].addtrip(itriplist.trips[i+1])
                                currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                                i += 1
                            else:

                                # Simulation is no longer in D and relocation has not been accepted.
                                # Pick the trip that followed the last conducted trip as next trip.

                                for itrip in self.y:
                                    if itrip.UIN == self.r[-1].trips[-1].UIN + 1:
                                        comingTrip = itrip
                                self.r[-1].addtrip(comingTrip)
                                self.r[-1].trips[-1].time_start = self.r[-1].trips[-2].time_end + \
                                                                 self.r[-1].trips[-2].idle_time
                                self.r[-1].trips[-1].time_end = self.r[-1].trips[-1].time_start + \
                                                               self.r[-1].trips[-1].rental_time
                                currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                    else:

                        # We DO NOT have at least one relevant tile.
                        # If simulation is still in d, take the subsequent trip as next trip.

                        if stillind:
                            self.r[-1].addtrip(itriplist.trips[i + 1])
                            currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                            i += 1
                        else:

                            # Simulation is no longer in D and we don't have at least one relevant tile.
                            # Pick the trip that followed the last conducted trip as next trip.

                            for itrip in self.y:
                                if itrip.UIN == self.r[-1].trips[-1].UIN + 1:
                                    comingTrip = itrip
                            self.r[-1].addtrip(comingTrip)
                            self.r[-1].trips[-1].time_start = self.r[-1].trips[-2].time_end + \
                                                             self.r[-1].trips[-2].idle_time
                            self.r[-1].trips[-1].time_end = self.r[-1].trips[-1].time_start + \
                                                           self.r[-1].trips[-1].rental_time
                            currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                else:

                    # We DO NOT have enough data to calculate an EIT for target tile.
                    # If simulation is still in d, take the subsequent trip as next trip.

                    if stillind:
                        self.r[-1].addtrip(itriplist.trips[i + 1])
                        currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time
                        i += 1
                    else:

                        # Simulation is no longer in D and we don't have enough data to calculate an EIT for target tile.
                        # Pick the trip that followed the last conducted trip as next trip.

                        for itrip in self.y:
                            if itrip.UIN == self.r[-1].trips[-1].UIN + 1:
                                comingTrip = itrip
                        self.r[-1].addtrip(comingTrip)
                        self.r[-1].trips[-1].time_start = self.r[-1].trips[-2].time_end + \
                                                         self.r[-1].trips[-2].idle_time
                        self.r[-1].trips[-1].time_end = self.r[-1].trips[-1].time_start + \
                                                       self.r[-1].trips[-1].rental_time
                        currenttime = self.r[-1].trips[-1].time_end + self.r[-1].trips[-1].idle_time

            # End of day has been reached.
            # Save data in output.

            print('Run ', len(self.r), ' of ', len(self.d), ' in w = ', str(threshold) , ' done.')
            self.r[-1].refresh()
            for t in self.r[-1].trips:
                header5 = (t.time_start, t.start['lat'], t.start['lon'], \
                           t.time_end, t.end['lat'], t.end['lon'], t.idle_time, \
                           t.rental_time, t.vin, t.UIN, t.tripsthisday, t.firstofday)
                writer5.writerow(header5)
                wr5file.flush()
            header6 = (self.r[-1].numberoftrips, self.r[-1].totalidle.total_seconds() / 60.0,\
                       self.r[-1].totalrental.total_seconds() / 60.0, \
                       self.r[-1].relocationsoffered, self.r[-1].relocationsaccepted)
            writer6.writerow(header6)
            wr6file.flush()
        wr5file.close()
        wr6file.close()
        wr7file.close()
        return 0

    # Function called from _main for setup of simulation.
    # Loads trips from database in _init folder.

    def loadtrips(self, firstday, lastday):
        self.firstday = firstday
        self.lastday = lastday

        # Identify all relevant vehicles through their Vehicle Identification Number (VIN).

        db = database
        query = "SELECT DISTINCT vin FROM berlin WHERE location = '%s' AND timestamp >= '%s' AND timestamp <= '%s'"% (self.location, self.firstday, self.lastday)
        vins = db.selectDataObjects(query, self.location)
        print('Found ', len(vins), ' vehicles in data source. Loading trip points...')

        # For each found car, create a car-object. Upon initialization, trips are loaded.

        i1 = 0
        for vin in vins:
            if i1 % 50 == 0:
                print(i1, ' of ', len(vins))
            v = car.car(vin, self)
            self.cars.append(v)
            i1 += 1
        self.writetrips(r'./_init/trips_raw.csv')

        # Not yet cleaned set of trips has been written to output.
        # Clean trip data and write cleaned data to output.

        self.cleantrips()
        self.writetrips(r'./_init/trips_cleaned.csv')

        # Load all trips, order them chronologically and write them to output.

        templist = list()
        for car1 in self.cars:
            for t in car1.trips:
                templist.append(t)
        self.x = sorted(templist, key=lambda trip: trip.time_start)
        self.writex(r'./_init/x_raw.csv')
        return 0

    # Function called from _main for setup of simulation.
    # Split trips into training set and test set according to specified percentage.

    def distributetrips(self, trainingpercentage):

        # Find the point of cutting the trip data into the 2 parts.
        # This point should be between 2 different car days.

        calcendofx = int(len(self.x)*float(float(trainingpercentage)/float(100.0)))
        endofx = calcendofx
        while self.x[endofx].time_start.date() == self.x[calcendofx].time_start.date():
            endofx += 1
        endofx = endofx - 1

        # Save training set (x) and test set (y).

        self.y = self.x[endofx + 1:len(self.x)]
        self.x = self.x[0 : endofx]
        self.writeanytrips(self.x, r'./_init/x.csv')

        # Give each trip a Unique Identification Number (UIN) that allows for
        # identification of following and preceding trips by iterating the UIN of a
        # known trip.

        self.x = sorted(self.x, key=lambda trip: trip.vin)
        self.y = sorted(self.y, key=lambda trip: trip.vin)
        iuin = 0
        for t in self.x:
            t.UIN = iuin
            iuin += 1
        for t in self.y:
            t.UIN = iuin
            iuin += 1
        self.writeanytrips(self.y, r'./_init/y.csv')

        # Identify all the first trips of car days and store in listoffirsts and in
        # firstofday marker for the trip.

        listoffirsts = list()
        tempnumberoftrips = 0
        for i3 in range(len(self.y)):
            tempnumberoftrips += 1
            if i3 == 0:
                self.y[i3].firstofday = True
                listoffirsts.append(self.y[i3])
            else:
                if i3 == len(self.y)-1:
                    self.y[i3].tripsthisday = tempnumberoftrips
                else:
                    if self.y[i3].time_start.date() != self.y[i3-1].time_start.date():
                        self.y[i3].firstofday = True
                        self.y[i3 - 1].tripsthisday = tempnumberoftrips
                        tempnumberoftrips = 0
                        listoffirsts.append(self.y[i3])

        # Store number of trips for each car day in the tripsthisday variable
        # for each trip.

        startnumber = 0
        for i3 in range(len(self.y)):
            if i3 == 0:
                startnumber = i3
            else:
                if i3 == len(self.y)-1:
                    for i5 in range(startnumber,i3+1):
                        self.y[i5].tripsthisday = self.y[i3].tripsthisday
                else:
                    if self.y[i3].firstofday == True:
                        for i5 in range(startnumber, i3):
                            self.y[i5].tripsthisday = self.y[i3-1].tripsthisday
                        startnumber = i3

        # Write results to output. Draw baseline of car days and save to 'd'.
        # Write 'd' to output.

        self.writeanytrips(listoffirsts, r'./_init/listoffirstsbefore.csv')
        random.shuffle(listoffirsts)
        self.writeanytrips(listoffirsts, r'./_init/listoffirstsafter.csv')
        listoffirsts = listoffirsts[0:self.numberofruns]
        for trip in listoffirsts:
            self.d.append(triplist.triplist(trip))
            for trip2 in self.y:
                if trip2.vin == trip.vin and \
                trip2.time_start.date() == trip.time_start.date() and \
                trip2.firstofday == False:
                    self.d[-1].addtrip(trip2)
        for t in self.d:
            t.refresh()
        self.writelistoftriplists(self.d, r'./_init/d.csv')
        self.writesummary(self.d, r'./_init/d_summary.csv')
        return 0

    # Function to save model using pickle.

    def save(self, path):
        try:
            print('Start saving model ' + path)
            f = open(path, mode='wb')
            pickle.dump(self, f)
        except IOError as e:
            print('Cannot save ' + path)
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
        else:
            print('Model ' + path + ' saved')

    # Function to load model using pickle.

    def load(self, path):
        try:
            print('Start loading model ' + path)
            f = open(path, mode='rb')
            model = pickle.load(f)
        except IOError:
            print('Cannot open' + path)
        else:
            print('Model ' + path + ' loaded')
            return model

    # Function to clean trip data.

    def cleantrips(self):

        # Take out trips that are out of date, that have negative idle
        # or rental time or that have rental time > 1 day

        for car in self.cars:
            for t in car.trips:
                if t.time_start.date() < self.firstday or \
                t.time_end.date() > self.lastday or \
                t.rental_time < datetime.timedelta(seconds=0) or \
                t.rental_time > datetime.timedelta(days=1) or \
                t.idle_time < datetime.timedelta(seconds=0):
                    t.start = 'POP'
        for car in self.cars:
            car.trips = [t for t in car.trips if t.start != 'POP']

        # Take out car days that do not end on next or any following day.

        flagtostay = True
        i4 = 0
        while flagtostay:
            flagtostay = False
            for car in self.cars:
                for t in range(len(car.trips)):
                    if t == len(car.trips) - 1:
                        newdate = car.trips[t].time_end + car.trips[t].idle_time
                        if newdate.date() == car.trips[t].time_start.date():
                            flagtostay = True
                            car.trips[t].start = 'POP'
                            i4 += 1
                    else:
                        newdate = car.trips[t].time_end + car.trips[t].idle_time
                        if newdate.date() == car.trips[t].time_start.date() and \
                            car.trips[t].time_start.date() != car.trips[t+1].time_start.date():
                            flagtostay = True
                            car.trips[t].start = 'POP'
                            i4 += 1
            for car in self.cars:
                car.trips = [t for t in car.trips if t.start != 'POP']
        print('Found ', i4, ' bad trips.')
        return 0

    # Functions to write data to output.

    def writetrips(self, path):
        wr1file = open(path, 'w')
        writer1 = csv.writer(wr1file, delimiter=";", lineterminator='\n')
        header1 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'IdleTime', 'RentalTime', 'Vin')
        writer1.writerow(header1)
        for car in self.cars:
            for t in car.trips:
                header1 = (t.time_start, t.start['lat'], t.start['lon'], \
                           t.time_end, t.end['lat'], t.end['lon'], t.idle_time,\
                           t.rental_time, t.vin)
                writer1.writerow(header1)
                wr1file.flush()
        wr1file.close()
        return 0

    def writex(self, path):
        wr2file = open(path, 'w')
        writer2 = csv.writer(wr2file, delimiter=";", lineterminator='\n')
        header2 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'IdleTime', 'RentalTime', 'Vin')
        writer2.writerow(header2)
        for t in self.x:
            header2 = (t.time_start, t.start['lat'], t.start['lon'], \
                t.time_end, t.end['lat'], t.end['lon'], t.idle_time,\
                t.rental_time, t.vin)
            writer2.writerow(header2)
            wr2file.flush()
        wr2file.close()
        return 0

    def writelistoftriplists(self, listoftriplists, path):
        wr4file = open(path, 'w')
        writer4 = csv.writer(wr4file, delimiter=";", lineterminator='\n')
        header4 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'IdleTime', 'RentalTime', 'Vin', 'UIN', 'Trips this day', 'First of day')
        writer4.writerow(header4)
        for triplist in listoftriplists:
            for t in triplist.trips:
                header4 = (t.time_start, t.start['lat'], t.start['lon'], \
                    t.time_end, t.end['lat'], t.end['lon'], t.idle_time,\
                    t.rental_time, t.vin, t.UIN, t.tripsthisday, t.firstofday)
                writer4.writerow(header4)
                wr4file.flush()
        wr4file.close()
        return 0

    def writeanytrips(self, trips, path):
        wr4file = open(path, 'w')
        writer4 = csv.writer(wr4file, delimiter=";", lineterminator='\n')
        header4 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'IdleTime', 'RentalTime', 'Vin', 'UIN', 'Trips this day', 'First of day')
        writer4.writerow(header4)
        for t in trips:
            header4 = (t.time_start, t.start['lat'], t.start['lon'], \
                t.time_end, t.end['lat'], t.end['lon'], t.idle_time,\
                t.rental_time, t.vin, t.UIN, t.tripsthisday, t.firstofday)
            writer4.writerow(header4)
            wr4file.flush()
        wr4file.close()
        return 0

    def writesummary(self, listoftriplists, path):
        wr4file = open(path, 'w')
        writer4 = csv.writer(wr4file, delimiter=";", lineterminator='\n')
        header4 = ('Number of Trips', 'Total Idle Time', 'Total Rental Time', 'Relocations offered', 'Relocations accepted')
        writer4.writerow(header4)
        for t in listoftriplists:
            header4 = (t.numberoftrips, t.totalidle.total_seconds()/60.0, t.totalrental.total_seconds()/60.0, t.relocationsoffered, t.relocationsaccepted)
            writer4.writerow(header4)
            wr4file.flush()
        wr4file.close()
        return 0

    # Function to set up tiles around destination of trips and return target tile.

    def initiatetiles(self, trip):
        self.tiles = list()

        # Determine edge lengths of tiles.

        deltalat = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                        (trip.end['lat'] + self.latdelta, trip.end['lon']), miles=False)
        deltalon = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                        (trip.end['lat'], trip.end['lon'] + self.londelta), miles=False)

        # Determine number of tiles to be created.

        numberCenterLat = math.floor(self.sigmaTiles/deltalat)
        numberCenterLon = math.floor(self.sigmaTiles/deltalon)
        numberInLat = int(round(numberCenterLat * 2.0 + 1.0))
        numberInLon = int(round(numberCenterLon * 2.0 + 1.0))
        rangeLat = range(numberInLat)
        rangeLon = range(numberInLon)

        # Set up tiles and save them to self.tiles.

        minLat = trip.end['lat'] - float(numberCenterLat) * self.latdelta
        minLon = trip.end['lon'] - float(numberCenterLon) * self.londelta
        result = 0
        for iLat in rangeLat:
            for iLon in rangeLon:
                lat = minLat + float(iLat) * self.latdelta
                lon = minLon + float(iLon) * self.londelta
                distance1 = haversine.haversine((trip.end['lat'], trip.end['lon']), (lat, lon), miles=False)
                if distance1 <= self.sigmaTiles :
                    self.tiles.append(tile.tile({'lat':lat, 'lon':lon}))
                    if lat == trip.end['lat'] and lon == trip.end['lon']:
                        result = self.tiles[-1]
        if result == 0:
            raise Exception('Initiatetiles flawed.')

        # Save all trips from x that are relevant for EIT calculation.

        latsigmaEIT = (self.sigmaEIT/deltalat)*self.latdelta
        lonsigmaEIT = (self.sigmaEIT/deltalon)*self.londelta
        for ix in self.x:
            for t in self.tiles:
                if ix.end['lat'] >= t.center['lat'] - latsigmaEIT and \
                                ix.end['lat'] < t.center['lat'] + latsigmaEIT and \
                                ix.end['lon'] >= t.center['lon'] - lonsigmaEIT and \
                                ix.end['lon'] < t.center['lon'] + lonsigmaEIT:
                    t.xtripstoend.append(ix)

        # Save all trips from y that are relevant as potential relocation trips.

        latsigmaY = (self.sigmaY / deltalat) * self.latdelta
        lonsigmaY = (self.sigmaY / deltalon) * self.londelta
        for iy in self.y:
            for t in self.tiles:
                if iy.end['lat'] >= t.center['lat'] - latsigmaY and \
                                iy.end['lat'] < t.center['lat'] + latsigmaY and \
                                iy.end['lon'] >= t.center['lon'] - lonsigmaY and \
                                iy.end['lon'] < t.center['lon'] + lonsigmaY:
                    t.ytripstoend.append(iy)
        return result

    # Function to calculate EIT for target tile.

    def getEITfromx(self, tile, time):
        eit = 0.0
        weight = 0.0
        for trip in tile.xtripstoend:
            tempdistance = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                               (tile.center['lat'], tile.center['lon']), \
                                               miles=False)
            if self.time_plus(datetime.time(trip.time_end.hour, trip.time_end.minute,\
                    trip.time_end.second), self.timewindowEIT) > time and\
                    datetime.time(trip.time_end.hour, trip.time_end.minute,\
                    trip.time_end.second) < self.time_plus(time, self.timewindowEIT) and\
                    tempdistance <= self.sigmaEIT:
                tempweight = self.calcweightEIT(tempdistance)
                weight += tempweight
                eit += (trip.idle_time.total_seconds() / 60.0) * tempweight
        if weight == 0.0:
            eit = None
        else:
            eit = eit / weight
        return eit

    # Function that returns all relevant tiles for given target tile.

    def getrelevantEIT(self, trip, tile, time, targettileEIT, threshold):
        result = list()
        for itile in self.tiles:

            # Find all relevant other tiles in viccinity of target tile.

            distance = haversine.haversine((trip.end['lat'], trip.end['lon']),\
                                      (itile.center['lat'], itile.center['lon']),\
                                       miles=False)
            if distance <= self.sigmaTiles and (itile.center['lat'] != tile.center['lat'] or itile.center['lon'] != tile.center['lon']):
                tempEIT = 0.0
                weight = 0.0
                for itrip in itile.xtripstoend:

                    # Find relevant trips from x for EIT calculation and calculate EIT.

                    tempdistance = haversine.haversine((itrip.end['lat'], itrip.end['lon']), \
                                                       (itile.center['lat'], itile.center['lon']), \
                                                       miles=False)
                    if self.time_plus(datetime.time(itrip.time_end.hour, itrip.time_end.minute,\
                            itrip.time_end.second), self.timewindowEIT) > time  and\
                            datetime.time(itrip.time_end.hour, itrip.time_end.minute,\
                            itrip.time_end.second) < self.time_plus(time, self.timewindowEIT) and\
                            tempdistance <= self.sigmaEIT:
                        tempweight = self.calcweightEIT(tempdistance)
                        tempEIT += (itrip.idle_time.total_seconds() / 60.0) * tempweight
                        weight += tempweight
                if weight == 0.0:
                    tempEIT = None
                else:
                    tempEIT = tempEIT / weight

                    # Continue calculation only if EIT of tile is lower that EIT of target tile less
                    # specified threshold.

                    if tempEIT < targettileEIT - threshold:
                        ytrips = list()
                        for itrip in itile.ytripstoend:
                            tempdistance = haversine.haversine((itrip.end['lat'], itrip.end['lon']), \
                                                               (itile.center['lat'], itile.center['lon']), \
                                                               miles=False)
                            if self.time_plus(datetime.time(itrip.time_end.hour, itrip.time_end.minute, \
                                itrip.time_end.second), self.timewindowEIT) > time and \
                                datetime.time(itrip.time_end.hour, itrip.time_end.minute, \
                                itrip.time_end.second) < self.time_plus(time, self.timewindowEIT) and\
                                itrip.UIN != trip.UIN and self.time_plus_extra(time, itrip.idle_time) == True and\
                                tempdistance <= self.sigmaY:
                                ytrips.append(itrip)

                        # Only return tile if there is at least one trip from y that could be used
                        # as relocation trip.

                        if ytrips != list():
                            result.append({'tile':itile,'EIT':tempEIT, 'trips':ytrips})
        if result == list():
            result = None
        return result

    # Function that finds the tile that is qualified and closest
    # to trip end and return the distance.

    def getclosesttile(self, relevantEIT, trip, tile):
        tempdistance = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                        (relevantEIT[0]['tile'].center['lat'], \
                                         relevantEIT[0]['tile'].center['lon']), \
                                        miles=False)
        result = tempdistance
        for i in relevantEIT:
            tempdistance = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                               (i['tile'].center['lat'], \
                                                i['tile'].center['lon']), \
                                               miles=False)
            if tempdistance < result:
                result = tempdistance
        return result

    # Function that returns acceptance probability based on specified probability
    # distribution and distance of offered relocation.

    def getaccprobability(self, offeredRelocation, probdistr):
        if probdistr == 'Linear':
            temp = (self.incentive - 100.0) / 100.0
            result = 1.0 + (offeredRelocation * temp / self.sigmaTiles)
        else:
            if probdistr == 'Gaussian':
                result = 1.1 * (math.exp(-2.397 * (pow((offeredRelocation / self.sigmaTiles), 2.0)))) - 0.1
            else:
                if probdistr == 'Logarithmic':
                    result = 1.1 * (math.pow(2.0, (offeredRelocation / self.sigmaTiles) / (-0.2890649))) - 0.1
                else:
                    if probdistr == 'Cosinus':
                        result = math.cos((offeredRelocation / self.sigmaTiles) * math.pi / 2.0)
        return result

    # Function that returns trip whose following trip will be used as
    # relocation trip.

    def picktrip(self, relevantEIT, trip):

        # Select tile from qualified tiles which will be used for relocation.
        # Save as selectedEIT.

        xk = ()
        pktemp = list()
        totalprobability = 0.0
        for i in range(len(relevantEIT)):
            xk = xk + (i,)
            tempdistance = haversine.haversine((trip.end['lat'], trip.end['lon']), \
                                               (relevantEIT[i]['tile'].center['lat'], \
                                                relevantEIT[i]['tile'].center['lon']), \
                                               miles=False)
            tempprobability = self.getQTprobability(tempdistance)
            pktemp.append(tempprobability)
            totalprobability += tempprobability
        for i in range(len(relevantEIT)):
            pktemp[i] = pktemp[i] / totalprobability
        pk = tuple(pktemp)
        relocQT = scipy.stats.rv_discrete(name='relocQT', values=(xk, pk))
        relocVar = relocQT.rvs()
        selectedEIT = relevantEIT[relocVar]

        # From relevant trips from y in selected tile, pick relocation trip.

        xk = ()
        pktemp = list()
        totalprobability = 0.0
        for i in range(len(selectedEIT['trips'])):
            xk = xk + (i,)
            tempdistance = haversine.haversine((selectedEIT['trips'][i].end['lat'], \
                                                selectedEIT['trips'][i].end['lon']), \
                                               (selectedEIT['tile'].center['lat'], \
                                                selectedEIT['tile'].center['lon']), \
                                           miles=False)
            tempprobability = self.getYTripprobability(tempdistance)
            pktemp.append(tempprobability)
            totalprobability += tempprobability
        for i in range(len(selectedEIT['trips'])):
            pktemp[i] = pktemp[i] / totalprobability
        pk = tuple(pktemp)
        relocY = scipy.stats.rv_discrete(name='relocY', values=(xk, pk))
        relocVar = relocY.rvs()
        tempdistance = haversine.haversine((trip.end['lat'], \
                                            trip.end['lon']), \
                                           (selectedEIT['tile'].center['lat'], \
                                            selectedEIT['tile'].center['lon']), \
                                           miles=False)
        result = [selectedEIT['trips'][relocVar], selectedEIT['EIT'], tempdistance]
        return result

    # Auxillary functions

    def time_plus(self, time, timedelta):
        start = datetime.datetime(2000, 1, 1, hour=time.hour, minute=time.minute, second=time.second)
        end = start + timedelta
        return end.time()

    def time_plus_extra(self, time, timedelta):
        start = datetime.datetime(2000, 1, 1, hour=time.hour, minute=time.minute, second=time.second)
        end = start + timedelta
        if start.date() == end.date():
            result = True
        else:
            result = False
        return result

    def calcweightEIT(self, distance):
        result = 1.0 - distance /self.sigmaEIT
        if result < 0.0:
            result = 0.0
        return result

    def calcweight(self, distance):
        result = 1.0 - distance / self.sigmaEIT
        if result < 0.0:
            result = 0.0
        return result

    def getQTprobability(self, distance):
        result = 1.0 - distance / self.sigmaTiles
        if result < 0.0:
            result = 0.0
        return result

    def getYTripprobability(self, distance):
        result = 1.0 - distance / self.sigmaY
        if result < 0.0:
            result = 0.0
        return result