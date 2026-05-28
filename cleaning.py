import pandas as pd

# CSV laden
df = pd.read_csv(
    "https://www.uvek-gis.admin.ch/BFE/ogd/35/ogd35_schweizerische_elektrizitaetsbilanz_monatswerte.csv"
)

# Datum erstellen
df["Datum"] = pd.to_datetime(
    dict(year=df["Jahr"], month=df["Monat"], day=1)
)

# Jahr und Monat löschen
df.drop(columns=["Jahr", "Monat"], inplace=True)

# Datum an erste Stelle
cols = ["Datum"] + [col for col in df.columns if col != "Datum"]
df = df[cols]

# Gewünschte Spalten
df = df[
    [
        "Datum",
        "Definitiv",
        "Erzeugung_Laufwerk_GWh",
        "Erzeugung_Speicherwerk_GWh",
        "Erzeugung_Kernkraftwerk_GWh",
        "Erzeugung_andere_GWh",
        "Erzeugung_Thermische_GWh",
        "Erzeugung_Windkraft_GWh",
        "Erzeugung_Photovoltaik_GWh"
    ]
]

# Klein schreiben
df.columns = df.columns.str.lower()



# Zahlenspalten finden
zahlenspalten = df.select_dtypes(include="number").columns

df[zahlenspalten] = (
    df[zahlenspalten]
    .round(0)
    .astype("Int64")
)
df = df.astype(str).replace(["<NA>", "NaN", "nan"], "")
print(df.head())
