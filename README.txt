Dear user,

We have set up a test data set for you to see if the code works properly. To check this, please follow these steps:
1) Keep "config.ini" structured as it is and place it in a folder called "_init" which should be located in the same directory that these python files are in.
2) Create a folder called "_results" which should be located in the same directory that these python files are in.
3) Ensure that the second line of "config.ini" says "Setup"
4) Run _main.py. If you receive any messages mentioning missing python packages, go ahead and install them and retry.
5) The setup simulation should not take more than a few minutes and should indicate its progress in the terminal.
6) After the setup, you should find 10 new files in the _init folder, one of which is our saved model "berlin_1.tmp". The _results folder should still be empty.
7) To run the simulation, change line 2 of "config.ini" to "Run" and run _main.py again.
8) Python should now perform a total of 200 runs - 100 for each threshold value which are preset to 10 and 20 (line 20 in "config.ini").
9) After the simulation, the files in "_init" should remain unaltered, but you find 6 new files in "_results":
    - For each threshold you find "eloc_<threshold>.csv", "k_<threshold>.csv" and "k_summary_<threshold>.csv".
    - "k_<threshold>.csv" contains the details for every simulated trip
    - "k_summary_<threshold>.csv" contains a summary for each vehicle (one row for each vehicle) with the number of trips, total idle time, total rental time, number of relocations offered, and number of relocations accepted.
    - "eloc_<threshold>.csv" contains all accepted and therefore conducted relocations