import model, ast, datetime

############################
### Read config.ini file ###
############################

# It is important to keep the config.ini file's
# structure in terms of order of lines.

path_config = r'./_init/config.ini'
initfile = open(path_config, 'r')
temp = initfile.readline()
setupmodel = initfile.readline()
setupmodel = setupmodel[0:len(setupmodel)-1]
temp = initfile.readline()
location = initfile.readline()
location = location[0:len(location)-1]
temp = initfile.readline()
modelnumber = initfile.readline()
modelnumber = modelnumber[0:len(modelnumber)-1]
temp = initfile.readline()
firstday = initfile.readline()
firstday = firstday[0:len(firstday)-1]
firstday = datetime.date(int(firstday[0:4]), int(firstday[5:7]), int(firstday[8:10]))
temp = initfile.readline()
lastday = initfile.readline()
lastday = lastday[0:len(lastday)-1]
lastday = datetime.date(int(lastday[0:4]), int(lastday[5:7]), int(lastday[8:10]))
temp = initfile.readline()
trainingpercentage = int(float(initfile.readline()))
temp = initfile.readline()
numberofruns = int(float(initfile.readline()))
temp = initfile.readline()
latdelta = 2.0 * float(initfile.readline())
temp = initfile.readline()
londelta = 2.0 * float(initfile.readline())
temp = initfile.readline()
w = initfile.readline()
w = ast.literal_eval(w)
temp = initfile.readline()
probdistr = initfile.readline()
probdistr = probdistr[0:len(probdistr)-1]
temp = initfile.readline()
incentive = initfile.readline()
incentive = incentive[0:len(incentive)-1]
initfile.close()

##############################
### Define names and paths ###
##############################

# Define name of model as <city>_<number of model>, e.g., Munich_2
temp = [location, '_', modelnumber]
modelname = "".join(temp)
# Define file of model as <city>_<number of model>.tmp
temp = [modelname, '.tmp']
modelfile = "".join(temp)
# Define path of model as \_init\<city>_<number of model>.tmp
temp = r'./_init/'
temp = [temp, modelfile]
modelpath = "".join(temp)

################################
### Set up and run the model ###
################################

if setupmodel == 'Setup':
    # Apparently, model needs to be set up and saved
    # This part is not designed to be parallelized
    print('Model number ', modelnumber, ' for ', location, ' with ', numberofruns, ' runs is being set up.')
    thismodel = model.model(location, numberofruns, latdelta, londelta)
    thismodel.loadtrips(firstday, lastday)
    thismodel.distributetrips(trainingpercentage)
    thismodel.save(modelpath)

else:
    # Apparently, model has already been set up, so we need to run the simulations
    # This part may be parallelized, e.g. use different machines for different w
    print('Model number ', modelnumber, ' for ', location, ' with ', numberofruns, ' runs is being run now.')
    thismodel = model.model().load(modelpath)
    thismodel.incentive = float(incentive)
    for wnow in w:
        thismodel.run(wnow, probdistr)