#!/usr/bin/python

import http.server
import socketserver
import os
import datetime
import threading
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tqdm import tqdm

PORT = int(os.environ.get("PORT", 5000))
def server_files():
    os.chdir('data')
    Handler = http.server.SimpleHTTPRequestHandler
    Handler.extensions_map.update({
        '.webapp': 'application/x-web-app-manifest+json',
    })

    httpd = socketserver.TCPServer(("", PORT), Handler)
    print("Serving at port", PORT)
    httpd.serve_forever()

def cleandata(df_raw):
    df_cleaned=df_raw.melt(id_vars=['Province/State','Country/Region','Lat','Long'],value_name='Cases',var_name='Date')
    df_cleaned=df_cleaned.set_index(['Country/Region','Province/State','Date'])
    return df_cleaned

def countrydata(df_cleaned,oldname,newname):
    df_country=df_cleaned.groupby(['Country/Region','Date'])['Cases'].sum().reset_index()
    df_country=df_country.set_index(['Country/Region','Date'])
    df_country.index=df_country.index.set_levels([df_country.index.levels[0], pd.to_datetime(df_country.index.levels[1])])
    df_country=df_country.sort_values(['Country/Region','Date'],ascending=True)
    df_country=df_country.rename(columns={oldname:newname})
    return df_country

def plotcountry(Country, CountryConsolidated):
    fig, axs = plt.subplots(3, 2)

    CountryConsolidated.loc[Country].reset_index().plot(ax=axs[0,0], style='.-', x='Date', y='Total Confirmed Cases')
    CountryConsolidated.loc[Country].reset_index().plot(ax=axs[0,1], style='.-', x='Date', y='Active Cases')
    CountryConsolidated.loc[Country].reset_index().plot(ax=axs[1,0], style='.-', x='Date', y='Total Deaths')
    CountryConsolidated.loc[Country].reset_index().plot(ax=axs[1,1], style='.-', x='Date', y='Total Recoveries')
    CountryConsolidated.loc[Country].reset_index().plot(ax=axs[2,0], style='.-', x='Date', y='Death to Cases Ratio')
    # CountryConsolidated.loc[Country].reset_index().plot(ax=axs[2,1], style='.-', x='Date', y='Total Confirmed Cases')
    # CountryConsolidated.plot()
    return fig

def dailydata(dfcountry,oldname,newname):
    dfcountrydaily=dfcountry.groupby(level=0).diff().fillna(0)
    dfcountrydaily=dfcountrydaily.rename(columns={oldname:newname})
    return dfcountrydaily

def update():
    ConfirmedCases=cleandata(pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv'))
    Deaths=cleandata(pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv'))
    Recoveries=cleandata(pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Recovered.csv'))

    ConfirmedCasesCountry=countrydata(ConfirmedCases,'Cases','Total Confirmed Cases')
    DeathsCountry=countrydata(Deaths,'Cases','Total Deaths')
    RecoveriesCountry=countrydata(Recoveries,'Cases','Total Recoveries')

    NewCasesCountry=dailydata(ConfirmedCasesCountry,'Total Confirmed Cases','Daily New Cases')
    NewDeathsCountry=dailydata(DeathsCountry,'Total Deaths','Daily New Deaths')
    NewRecoveriesCountry=dailydata(RecoveriesCountry,'Total Recoveries','Daily New Recoveries')

    CountryConsolidated=pd.merge(ConfirmedCasesCountry,NewCasesCountry,how='left',left_index=True,right_index=True)
    CountryConsolidated=pd.merge(CountryConsolidated,NewDeathsCountry,how='left',left_index=True,right_index=True)
    CountryConsolidated=pd.merge(CountryConsolidated,DeathsCountry,how='left',left_index=True,right_index=True)
    CountryConsolidated=pd.merge(CountryConsolidated,RecoveriesCountry,how='left',left_index=True,right_index=True)
    CountryConsolidated=pd.merge(CountryConsolidated,NewRecoveriesCountry,how='left',left_index=True,right_index=True)
    CountryConsolidated['Active Cases']=CountryConsolidated['Total Confirmed Cases']-CountryConsolidated['Total Deaths']-CountryConsolidated['Total Recoveries']
    CountryConsolidated['Share of Recoveries - Closed Cases']=np.round(CountryConsolidated['Total Recoveries']/(CountryConsolidated['Total Recoveries']+CountryConsolidated['Total Deaths']),2)
    CountryConsolidated['Death to Cases Ratio']=np.round(CountryConsolidated['Total Deaths']/CountryConsolidated['Total Confirmed Cases'],3)

    Countries = []
    for ind in list(ConfirmedCasesCountry.index):
        Countries += [ind[0]]

    Countries = np.unique(Countries)
    # print(CountryConsolidated)
    cs = (CountryConsolidated['Total Confirmed Cases'] != 0).groupby(level=0).cumsum()
    countryConsolidated = CountryConsolidated.drop(cs[cs == 0].index)
    for country in tqdm(Countries):
        fig = plotcountry(country, countryConsolidated)
        fig.savefig(country + ".png", dpi=300)
        plt.close()

def main():
    threading.Thread(target=server_files).start()
    update()

main()