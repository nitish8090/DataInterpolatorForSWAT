path = r"D:\Nitish\2102_Feb\10_WeatherPoints\Data\Input"
import os
n = os.listdir(path)

a = [f for f in n if not f.endswith(".zip")]
print(a)