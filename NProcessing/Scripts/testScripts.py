import pandas as pd

data = [['tom', 10, 5], ['nick', 15, 6], ['juli', 14, 6]]

# Create the pandas DataFrame
df = pd.DataFrame(data, columns=['Name', 'Age', 'n'])
df = df[['Name', 'n']]
print(df.to_csv(index=False, header=False))