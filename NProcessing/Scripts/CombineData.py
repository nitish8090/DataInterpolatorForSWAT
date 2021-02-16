import os
import csv
import pandas as pd
import numpy as np
from collections import namedtuple
import time
import tkinter as tk
from tkinter.filedialog import askopenfile


class WeatherDataFiles:
    """Class for all the weather files downloaded from weather site"""

    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.files = {}

    def set_list_of_files(self):
        for csv_file in os.listdir(self.folder_path):
            if csv_file.startswith("weatherdata") and csv_file.endswith(".csv"):
                code = 'p' + os.path.splitext(csv_file)[0].split("-")[1]
                self.files[code] = WeatherDataFile()
                self.files[code].set_path(os.path.join(self.folder_path, csv_file))
                self.files[code].read_df()
                # "weatherdata-236728.csv"

    def get_known_point_df(self):
        df = pd.DataFrame(columns=['Name', 'Longitude', 'Latitude'])
        for f in self.files:
            df.loc[len(df.index)] = {'Name': f, 'Latitude': self.files[f].lat, 'Longitude': self.files[f].long}
        return df

    def get_date_list(self):
        return self.files[list(self.files.keys())[0]].df.index


class WeatherDataFile:
    """Individual watershed datafile, its data frame and related property"""

    def __init__(self):
        self.df = None
        self.path = None
        self.lat = self.long = None
        self.code = None

    def set_path(self, path):
        self.path = path
        self.code = os.path.splitext(os.path.split(self.path)[1])[0].split("-")[1]

    def read_df(self):
        self.df = pd.read_csv(self.path, index_col=False)
        self.lat = self.df.Latitude[0]
        self.long = self.df.Longitude[0]
        self.df.set_index('Date', inplace=True, drop=True)


class KnownPoints:
    def __init__(self):
        self.df = None

    def set_df(self, df):
        self.df = df


class RandomPoints:
    """Points for which the values need to be interpolated"""

    def __init__(self, path):
        self.path = path
        self.df = None
        self.lat_header = ''
        self.long_header = ''
        self.points = []

    def read_dataframe(self):
        self.df = pd.read_csv(self.path)

    def set_lat_long_header(self, lat, long):
        self.lat_header = lat
        self.long_header = long

    def create_individual_random_point(self):
        for row in self.df.itertuples():
            self.points.append(IndividualRandomPoint(getattr(row, self.lat_header), getattr(row, self.long_header)))


class IndividualRandomPoint:
    """Individual Random Point"""

    def __init__(self, lat, long):
        self.lat = lat
        self.long = long
        self.nearDF = None
        self.mainDF = None

    def set_known_point_dataframes(self, known_points_dataframe):
        """Make a copy of dataframe and calculate distance"""
        self.nearDF = known_points_dataframe.copy()
        self.nearDF.set_index('Name', inplace=True)
        # self.nearDF['Distance'] = np.nan

    def calculate_distance(self):
        self.nearDF['Distance'] = ((self.nearDF.Latitude - self.lat) ** 2 + (
                self.nearDF.Longitude - self.long) ** 2) ** 0.5
        # self.nearDF['InvDistanceSq'] = 1 / (self.nearDF.Distance ** 2)

    def set_search_radius(self, radius):
        self.nearDF = self.nearDF.loc[self.nearDF.loc[:, 'Distance'] > radius]

    def create_main_dataframe(self, date_df):
        self.mainDF = pd.DataFrame(date_df)
        self.mainDF['Longitude'] = self.long
        self.mainDF['Latitude'] = self.lat
        self.mainDF.set_index('Date', inplace=True)

    def calculate_pixel_values(self, weather_data_files):
        start = time.time()

        # TODO: Make this function accept all values
        attributes = ['Elevation', 'Max Temperature', 'Min Temperature', 'Precipitation', 'Wind',
                      'Relative Humidity', 'Solar']
        pow = 2
        self.mainDF = pd.concat([self.mainDF, pd.DataFrame(columns=attributes)])
        denominator = (1 / (self.nearDF.Distance ** 2)).sum()
        done_list = []
        for i, date in enumerate(self.mainDF.index):
            n = int((i / len(self.mainDF.index)) * 100)
            if n % 10 == 0 and not np.isin(n, done_list):
                print(" {}%".format(n), end='')
                done_list.append(n)

            # print("Date: {}".format(date))
            copy_nearDF = self.nearDF.copy()  # Make a temporary data frame for each date

            for nearpoint in copy_nearDF.index:
                # Append Value to each point from the weather file
                copy_nearDF.loc[nearpoint, attributes] = weather_data_files.files[nearpoint].df.loc[date][2:]
            copy_nearDF[attributes] = copy_nearDF[attributes].div(copy_nearDF.Distance ** pow, axis=0)
            copy_nearDF.loc['Total'] = pd.Series(copy_nearDF[attributes].sum())

            for a in attributes:
                self.mainDF.loc[[date], a] = copy_nearDF.loc['Total'].loc[a] / denominator
        end = time.time()
        print("This took: {}".format(end - start))


def main():
    input_data_path = r"E:\Watershed_work_data\WeatherDataInterpolator\NProcessing\InputData\38166_2021-02-13-08-18-25\38166_2021-02-13-08-18-25"

    random_points = RandomPoints(
        r"E:\Watershed_work_data\WeatherDataInterpolator\NProcessing\InputData\RandomPoints.csv")
    random_points.set_lat_long_header(lat='Lat', long='Long')
    random_points.read_dataframe()
    random_points.create_individual_random_point()

    weather_data_files = WeatherDataFiles(folder_path=os.path.join(input_data_path))
    weather_data_files.set_list_of_files()

    known_points = KnownPoints()
    known_points.set_df(weather_data_files.get_known_point_df())

    for i, point in enumerate(random_points.points):
        print("Processing [{}/{}]".format(i + 1, len(random_points.points)))
        point.set_known_point_dataframes(known_points_dataframe=known_points.df)
        point.calculate_distance()
        point.set_search_radius(radius=0.3)
        print("Working for Lat: {}, Long: {}".format(point.lat, point.long))
        point.create_main_dataframe(date_df=weather_data_files.get_date_list())
        point.calculate_pixel_values(weather_data_files=weather_data_files)
        print("Main Data frame:")
        print(point.mainDF)

def start():
    
def callback():
    a = tk.filedialog.askdirectory()
    print(a)


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        # tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        strvar = tk.StringVar(self.parent, "Hello !")
        weather_data_label = tk.Entry(self.parent, text=strvar)
        weather_data_label.pack()

        unknown_point_lable = tk.Entry(self.parent)
        unknown_point_lable.pack()

        self.weather_data_button = tk.Button(self.parent, text="Where is the weather data?", command=callback)
        self.weather_data_button.pack()

        self.random_points_button = tk.Button(self.parent, text="Where is the CSV for Unknown Points?", command=callback)
        self.random_points_button.pack()

        self.start_process_button = tk.Button(self.parent, text="START", command=start)
        self.start_process_button.pack()

        # <create the rest of your GUI here>


if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()
