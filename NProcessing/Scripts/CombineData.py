import os
import csv
import pandas as pd
import numpy as np
from collections import namedtuple
from itertools import product
from functools import partial
import time
import tkinter as tk
from tkinter.filedialog import askopenfile
import multiprocessing
import datetime

name_converter = {'Max Temperature': 'tmp', 'Precipitation': 'pcp', 'Wind': 'wind',
                  'Relative Humidity': 'rh', 'Solar': 'solar'}


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
        for i, row in enumerate(self.df.itertuples()):
            point = IndividualRandomPoint(getattr(row, self.lat_header), getattr(row, self.long_header))
            point.set_index(i)
            self.points.append(point)


class IndividualRandomPoint:
    """Individual Random Point"""

    def __init__(self, lat, long):
        self.lat = lat
        self.long = long
        self.nearDF = None
        self.mainDF = None
        self.index = None

    def set_index(self, i):
        self.index = i

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

    def calculate_pixel_values(self, weather_data_files, pow=2):
        start = time.time()

        # TODO: Make this function accept all values
        attributes = ['Elevation', 'Max Temperature', 'Min Temperature', 'Precipitation', 'Wind',
                      'Relative Humidity', 'Solar']

        self.mainDF = pd.concat([self.mainDF, pd.DataFrame(columns=attributes)])
        denominator = (1 / (self.nearDF.Distance ** 2)).sum()
        done_list = []
        for i, date in enumerate(self.mainDF.index):
            # Progress bar
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

    def write_to_csv(self, output_location):
        def convert_date(date):
            x = datetime.datetime.strptime(date, '%m/%d/%Y')
            return x.strftime("%Y%m%d")

        elevation = self.mainDF.Elevation[0]
        for col in self.mainDF.columns:
            # Write Data in data files
            if col in ['Longitude', 'Latitude', 'Elevation']:
                pass
            elif col in ['Max Temperature', 'Min Temperature']:
                pass
            else:
                file_name = name_converter[col][0] + str(self.index)
                out_path = os.path.join(output_location, file_name + '.txt')
                with open(out_path, 'w') as a_file:
                    a_file.write(convert_date(date=self.mainDF.index[0]))
                    a_file.write("\n")
                self.mainDF[col].to_csv(out_path, mode='a', index=False, header=False)

            # Write Data in Info files
            if col in ['Longitude', 'Latitude', 'Elevation']:
                pass
            elif col in ['Min Temperature']:
                pass
            else:
                file_name = name_converter[col][0] + str(self.index)
                info_file_name = name_converter[col] + '.txt'
                info_out_path = os.path.join(output_location, info_file_name)
                ex_dict = {'ID': self.index, 'NAME': file_name, 'LAT': self.lat, 'LONG': self.long,
                           'ELEVATION': elevation}
                with open(info_out_path, 'a', newline="") as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=['ID', 'NAME', 'LAT', 'LONG', 'ELEVATION'])
                    writer.writerow(ex_dict)

        # Write Temperature files
        temp_txt_path = os.path.join(output_location, 't' + str(self.index) + '.txt')
        new_df = self.mainDF[['Max Temperature', 'Min Temperature']]
        with open(temp_txt_path, 'w') as a_file:
            a_file.write(convert_date(date=self.mainDF.index[0]))
            a_file.write("\n")
        new_df.to_csv(temp_txt_path, mode='a', index=False,header=False)


def main():
    input_data_path = r"D:\Nitish\2102_Feb\10_WeatherPoints\NProcessing\InputData\38166_2021-02-13-08-18-25\38166_2021-02-13-08-18-25"
    output_location = r"D:\Nitish\2102_Feb\10_WeatherPoints\NProcessing\OutputData\Test1"

    random_points = RandomPoints(
        r"D:\Nitish\2102_Feb\10_WeatherPoints\NProcessing\InputData\RandomPoints.csv")
    random_points.set_lat_long_header(lat='Lat', long='Long')
    random_points.read_dataframe()
    random_points.create_individual_random_point()

    weather_data_files = WeatherDataFiles(folder_path=os.path.join(input_data_path))
    weather_data_files.set_list_of_files()

    known_points = KnownPoints()
    known_points.set_df(weather_data_files.get_known_point_df())

    # Create info files
    for key in name_converter.keys():
        file_name = name_converter[key] + '.txt'
        file_path = os.path.join(output_location, file_name)
        with open(file_path, 'w', newline="") as a_file:
            a_file.write('ID,NAME,LAT,LONG,ELEVATION')
            a_file.write("\n")

    with multiprocessing.Pool(processes=8) as pool:
        pool.map(partial(execute, known_points=known_points, weather_data_files=weather_data_files,
                         output_location=output_location), random_points.points)

    # for i, point in enumerate(random_points.points):
    #     print("Processing [{}/{}]".format(i + 1, len(random_points.points)))
    #     execute(point)


def execute(point, known_points, weather_data_files, output_location):
    # global known_points, weather_data_files, output_location
    point.set_known_point_dataframes(known_points_dataframe=known_points.df)
    point.calculate_distance()
    point.set_search_radius(radius=0.3)
    print("Working for Lat: {}, Long: {}".format(point.lat, point.long))
    point.create_main_dataframe(date_df=weather_data_files.get_date_list())
    point.calculate_pixel_values(weather_data_files=weather_data_files)
    print("Main Data frame:")
    print(point.mainDF)

    print("Writing to CSV")
    point.write_to_csv(output_location=output_location)


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.parent.title("WeatherData Interpolator")

        # Weather Location Folder
        self.weather_location_string_var = tk.StringVar(self.parent, "Weather Data Folder")
        self.weather_data_label = tk.Entry(self.parent, text=self.weather_location_string_var)
        self.weather_data_label.config(fg='grey')
        self.weather_data_label.pack()

        self.weather_data_button = tk.Button(self.parent, text="Where is the weather data?",
                                             command=self.set_weather_data)
        self.weather_data_button.pack()

        # Unknown Point Location
        self.unknown_point_label_string_var = tk.StringVar(self.parent, "Unknown Point Location")
        self.unknown_point_label = tk.Entry(self.parent, text=self.unknown_point_label_string_var)
        self.unknown_point_label.pack()

        self.random_points_button = tk.Button(self.parent, text="Where is the CSV for Unknown Points?",
                                              command=self.set_random_point)
        self.random_points_button.pack()

        # Output Location
        self.output_location_string_var = tk.StringVar(self.parent, "Output Location")
        self.output_location_entry = tk.Entry(self.parent, text=self.output_location_string_var)
        self.output_location_entry.pack()
        self.output_location_btn = tk.Button(self.parent, text="Output Location", command=self.set_output_location)
        self.output_location_btn.pack()

        # Start Button
        self.start_process_button = tk.Button(self.parent, text="START")
        self.start_process_button.pack()

    def set_weather_data(self):
        a = tk.filedialog.askdirectory()
        self.weather_location_string_var.set(a)
        self.weather_data_label.config(fg='black')

    def set_random_point(self):
        a = tk.filedialog.askopenfile()
        self.unknown_point_label_string_var.set(a)

    def set_output_location(self):
        a = tk.filedialog.askdirectory()
        self.output_location_string_var.set(a)


# if __name__ == "__main__":
#     root = tk.Tk()
#     root.geometry("600x300")
#     app = MainApplication(root)
#     root.mainloop()

# global known_points, weather_data_files, output_location
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
