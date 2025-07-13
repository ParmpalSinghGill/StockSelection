import pandas as pd

def filterMfFunds():
    df=pd.read_csv("groww_mutual_funds.csv")
    df.pop("Unnamed: 0")
    df=df[df["Rating"]=="5"]
    df=df[df["5Y"]!="--"]
    # print(df.columns)
    # print(df["5Y"].unique())
    df["5Y"]=df["5Y"].map(lambda x:float(x.removesuffix("%")))
    df=df[df["5Y"]>20]
    # print(df["5Y"].unique())
    # print(df.shape)
    # # df=df[d]
    return {row["Fund Name (1,542 results)"]:row["Link"] for i,row in df.iterrows()}

if __name__ == '__main__':
    print(filterMfFunds())
