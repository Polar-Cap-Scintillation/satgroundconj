# tle.py

# Propigates satellite position at a particular time given a Two Line Element.
# Based primarially off of Vallado 2006
# Requires the sgp4 package (https://pypi.org/project/sgp4/)
# References:
#   Vallado, D. A., Crawford, P., Hujsak, R., and Kelso, T. S. (2006). "Revisiting Spacetrack Report #3",
#       presented at the AIAA/AAS Astrodynamics Specialist Converence, Keystone, CO, 2006 August 21-24.
#   Zhu, J. (1994). Conversion of Earth-centered Earth-fixed coordinates to geodetic coordinates.
#       IEEE Trans Aerosp Electron Syst, 30(3): 957-961. doi: 10.1109/7.303772

# It violates space-track.org's usage policy to make too many API queries.  This
#   code predownloads all TLEs for the satellite of interest and saves them in a
#   local directory defined in space_track_credentials.  To force this code to 
#   update all TLEs, just delete the contents fo this directory and let it
#   request the latest TLE files.

# NEW
# BULK DOWNLOAD OF ALL TLE
# https://ln5.sync.com/dl/afd354190/c5cd2q72-a5qjzp4q-nbjdiqkr-cenajuqu
#

### SGP4 library seems to like to use julian date as an epoch, so we will too.

###############################################################
# TODO
# - add command line script for generating TLE database
################################################################





import os
import numpy as np
import datetime as dt
import pymap3d as pm
from tqdm import tqdm
import argparse

from sgp4.api import Satrec, WGS72, jday
from sgp4 import exporter
from sgp4.conveniences import sat_epoch_datetime
from skyfield.api import EarthSatellite, load, wgs84

import sqlalchemy
from sqlalchemy import Column, Integer, Float
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import declarative_base, Session



# Define class that will be used to create TLE SQL database
Base = declarative_base()

class TLE(Base):
    __tablename__ = 'tle'
    id = Column(Integer, primary_key = True)
    satnum = Column(Integer, nullable=False, index=True)
    epoch = Column(Float, nullable=False)
    bstar = Column(Float, nullable=False)
    ndot = Column(Float, nullable=False)
    nddot = Column(Float, nullable=False)
    ecco = Column(Float, nullable=False)
    argpo = Column(Float, nullable=False)
    inclo = Column(Float, nullable=False)
    mo = Column(Float, nullable=False)
    no_kozai = Column(Float, nullable=False)
    nodeo = Column(Float, nullable=False)



def create_sql_database(source_files, dbfile='tle.db'):
    """
    Generate TLE SQL database from source text files.
    Text files can be downloaded in bulk from:
    https://ln5.sync.com/dl/afd354190/c5cd2q72-a5qjzp4q-nbjdiqkr-cenajuqu
    (This is the space-track.org bulk download site, not something sketchy.)
    """

    if os.path.exists(dbfile):
        raise FileExistsError(f'File {dbfile} already exists!')

    engine = create_engine(f"sqlite:///{dbfile}", echo=False)
    Base.metadata.create_all(engine)
    
    numfiles = len(source_files)    # Number of input files for progress tracking

    with Session(engine) as session:

        i = 0       # unique id counter
        for fi, srcfile in enumerate(source_files):
            print(f'[{fi+1}/{numfiles}] {srcfile}')

            # Count number of lines in file
            with open(srcfile, 'rb') as f:
                #num_lines = sum(1 for line in f)
                num_lines = sum(1 for _ in f)
 
            with open(srcfile, 'r') as f:
                for l1 in tqdm(f, total=num_lines/2):
                    l2 = f.readline()
           
                    try:
                        sgp4obj = Satrec.twoline2rv(l1, l2)
                    except ValueError as e:
                        # Put this in an error log
                        #print(e)
                        #print(len(l1), len(l2))
                        #print('LINE 1:', l1)
                        #print('LINE 2:', l2)
                        continue
       

                    sqlobj = sgp2sql(sgp4obj, i)
                    session.add(sqlobj)

                    i += 1

            print('Committing to SQL database ...')
            session.commit()


def cli_create_database():
    """
    CLI fuction to generate TLE SQL database from source files
    """
    parser = argparse.ArgumentParser(prog='create-tle-db',
                                     description='Generate TLE database from source files.')
    parser.add_argument('input', nargs='+', help='input source txt files')
    parser.add_argument('-o', '--output', help='output db file')
    args = parser.parse_args()

    create_sql_database(args.input, dbfile=args.output)



def sgp2sql(sgp4obj, i):
    """
    Convert a sgp4.Satrec objet to a TLE obect for SQL databae.
    """

    # Calculate Julian day epoch
    jd_epoch = sgp4obj.jdsatepoch + sgp4obj.jdsatepochF

    tleobj = TLE(id=i,
                 satnum   = sgp4obj.satnum,
                 epoch    = jd_epoch,
                 bstar    = sgp4obj.bstar,
                 ndot     = sgp4obj.ndot,
                 nddot    = sgp4obj.nddot,
                 ecco     = sgp4obj.ecco,
                 argpo    = sgp4obj.argpo,
                 inclo    = sgp4obj.inclo,
                 mo       = sgp4obj.mo,
                 no_kozai = sgp4obj.no_kozai,
                 nodeo    = sgp4obj.nodeo)

    return tleobj
        

def sql2sgp(sqlobj):
    """
    Convert a SQL database TLE obect to a sgp4.Satrec object.
    """

    #To compute the “epoch” argument, take the epoch’s Julian date and subtract 2433281.5 days.
    epoch = sqlobj.epoch - 2433281.5

    sgp4obj = Satrec()
    sgp4obj.sgp4init(
                     WGS72,                 # gravity model
                     'i',                   # 'a' = old AFSPC mode, 'i' = improved mode
                     sqlobj.satnum,         # satnum: Satellite number
                     epoch,                 # epoch: days since 1949 December 31 00:00 UT
                     sqlobj.bstar,          # bstar: drag coefficient (1/earth radii)
                     sqlobj.ndot,           # ndot: ballistic coefficient (radians/minute^2)
                     sqlobj.nddot,          # nddot: mean motion 2nd derivative (radians/minute^3)
                     sqlobj.ecco,           # ecco: eccentricity
                     sqlobj.argpo,          # argpo: argument of perigee (radians 0..2pi)
                     sqlobj.inclo,          # inclo: inclination (radians 0..pi)
                     sqlobj.mo,             # mo: mean anomaly (radians 0..2pi)
                     sqlobj.no_kozai,       # no_kozai: mean motion (radians/minute)
                     sqlobj.nodeo,          # nodeo: R.A. of ascending node (radians 0..2pi)
                    )

    return sgp4obj


class TLEHandler(object):
    def __init__(self, dbfile='tle.db'):

        self.load_db(dbfile)


    def load_db(self, dbfile):

        engine = create_engine(f"sqlite:///{dbfile}", echo=False)
        self.session = Session(engine)


    def select_tles(self, sat_cat, time0, time1, jd_epoch=False):

        sat_cat = int(sat_cat)

        jd0, fr0 = jday(time0.year, time0.month, time0.day, time0.hour, time0.minute, time0.second)
        jdtime0 = jd0 + fr0
        jd1, fr1 = jday(time1.year, time1.month, time1.day, time1.hour, time1.minute, time1.second)
        jdtime1 = jd1 + fr1


        # All TLEs between first and last time
        conditions = sqlalchemy.and_(TLE.satnum==sat_cat,
                                     TLE.epoch>=jdtime0,
                                     TLE.epoch<=jdtime1)
        tle_between = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).all()

        # Last epoch before first time
        conditions = sqlalchemy.and_(TLE.satnum==sat_cat,
                                      TLE.epoch<jdtime0)
        tle_first = self.session.query(TLE).filter(conditions).order_by(desc(TLE.epoch)).first()

        # First epoch after last time
        conditions = sqlalchemy.and_(TLE.satnum==sat_cat,
                                      TLE.epoch>jdtime1)
        tle_last = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).first()

        # Create full list
        tle_list = [tle_first] + tle_between + [tle_last]

        # Extract array of epoch times
        if jd_epoch:
            # Extract as Julian days
            epoch_list = [t.epoch for t in tle_list]
        else:
            # Extract as datetime objects
            epoch_list = [sat_epoch_datetime(sql2sgp(t)) for t in tle_list]

        # Return epochs as datetime objects UNLESS JD flag set
        return epoch_list, tle_list


    def sat_position(self, sat_cat, time_array):
        # Note: This function only works for sequential times

        sat_cat = int(sat_cat)

        jd_array = np.array([jday(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time_array])

        # Get all TLEs that fall in time range
        epoch_list, tle_list = self.select_tles(sat_cat, time_array[0], time_array[-1], jd_epoch=True)

        # Find index of epoch closest to each time in the time array
        closest_epoch_idx = np.array([np.argmin(np.abs(t-epoch_list)) for t in jd_array])

        # Somewhere in here check that epoch is within 10 days and if not, raise warning

        # Cycle through epochs and calculate position for satellite for each one when that epoch is the closest time
        sat_position = np.empty((3,0))

        for i in np.unique(closest_epoch_idx):
            # Select subset of times closest to a particular epoch
            subset_times = np.array(time_array)[closest_epoch_idx==i]

            sgp4obj = sql2sgp(tle_list[i])

            line1, line2 = exporter.export_tle(sgp4obj)

            # calcualte satellite position using functions from TLE propgation script
            X, Y, Z = propagate_tle2(subset_times, line1, line2)
            sat_position = np.append(sat_position, np.array([X, Y, Z]), axis=1)

        return sat_position




# This can probably be made more efficient by doing the satelite propagation directly
#   with the sgp4 pacakge and only using skyfield for coordinate conversion.
#   This is sort of done in propagate_tle3(), but it's not quite right.
def propagate_tle2(time0, tleline1, tleline2):

    ts = load.timescale()
    satellite = EarthSatellite(tleline1, tleline2)
   
    tmp = np.array([[t.year, t.month, t.day, t.hour, t.minute, t.second] for t in time0])
    tstmp = ts.utc(tmp[:,0], tmp[:,1], tmp[:,2], tmp[:,3], tmp[:,4], tmp[:,5])

    geocentric = satellite.at(tstmp)

    posobj = wgs84.geographic_position_of(geocentric)
   
    return posobj.itrs_xyz.m



def propagate_tle3(time0, tleline1, tleline2):

    # initialize tle object
    tle = Satrec.twoline2rv(tleline1, tleline2)

    out = [jday(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time0]
    jd, fr = np.array(out, order='F').T     # order='F' needed for some kind of error not contiguous in C error when passed into sgp4_array() ???
    e, r, v = tle.sgp4_array(jd, fr)
    #print(r.shape, v.shape)


    #posobj = TEME(r)

    r,v = sgp4lib.TEME_to_ITRF(jd+fr, r, v)
    print(r.shape)

    fig, ax = plt.subplots(subplot_kw={'projection':'3d'})
    #ax.plot(position[0], position[1], position[2])
    ax.plot(posobj.itrs_xyz.km[0], posobj.itrs_xyz.km[1], posobj.itrs_xyz.km[2])
    plt.show()




#def propagate_tle(time0, tleline1, tleline2):
#    # time0 is an array of datetime objects that the satellite position is to be calculated at
#    # TLE is a list consisting of the first and second lines of the TLE as strings ([TLE line 1, TLE line 2])
#
#    # Note: This function returns satellite position in Pseudo Earth-Fixed (PEF) coordinates, which are
#    #   assumed to be approximately equal to Earth-Centered, Earth-Fixed (ECEF) coordinates.  This does NOT
#    #   account for polar motion (precession, nutation).  For discussion of a "proper" PEF->ECEF transformation,
#    #   please refer to Vallado et al., 2006 Appendix C or Panigrahi and Gaurav, 2015
#    #   (https://mycoordinates.org/tracking-satellite-footprints-on-earth%E2%80%99s-surface/)
#
#    #X = []
#    #Y = []
#    #Z = []
#
#
#
#    # initialize tle object
#    tle = Satrec.twoline2rv(tleline1, tleline2)
#
#
##    epoch1949s = (dt.datetime(1949,12,31) - dt.datetime.fromtimestamp(0)).total_seconds()
##    epoch1949  = (tleinfo.epoch-epoch1949s)/(24.*60.*60.)
##
##    tle = Satrec()
##    tle.sgp4init(
##        wgs72,                # gravity model
##        'i',                  # 'a' = old AFSPC mode, 'i' = improved mode
##        tleinfo.satnum,                # satnum: Satellite number
##        epoch1949,       # epoch: days since 1949 December 31 00:00 UT
##        tleinfo.bstar,           # bstar: drag coefficient (1/earth radii)
##        tleinfo.ndot,                  # ndot: ballistic coefficient (radians/minute^2)
##        tleinfo.nddot,                  # nddot: mean motion 2nd derivative (radians/minute^3)
##        np.deg2rad(tleinfo.ecco),            # ecco: eccentricity
##        np.deg2rad(tleinfo.argpo),   # argpo: argument of perigee (radians 0..2pi)
##        np.deg2rad(tleinfo.inclo),   # inclo: inclination (radians 0..pi)
##        np.deg2rad(tleinfo.mo),   # mo: mean anomaly (radians 0..2pi)
##        np.deg2rad(tleinfo.no_kozai),  # no_kozai: mean motion (radians/minute)
##        np.deg2rad(tleinfo.nodeo),    # nodeo: R.A. of ascending node (radians 0..2pi)
##    )
#
#
#    #out = jday(t)
#    out = [jday(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time0]
#    jd, fr = np.array(out, order='F').T     # order='F' needed for some kind of error not contiguous in C error when passed into sgp4_array() ???
#    print(jd.flags)
#    print(fr.flags)
#    #jd = np.ascontiguousarray(jd)
#    #fr = np.ascontiguousarray(fr)
#    e, position, velocity = tle.sgp4_array(jd, fr)
#    #print(r.shape, v.shape)
#
#
#
#    fig, ax = plt.subplots(subplot_kw={'projection':'3d'})
#    ax.plot(position[0], position[1], position[2])
#    plt.show()
#
#
##    for t in time0:
#
#    # calculate satellite position/velocity in True Equator, Mean Equinox [TEME] (units of km and km/s)
#    #position, velocity = tle.propagate(t.year,month=t.month,day=t.day,hour=t.hour,minute=t.minute,second=t.second)
#    #jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second)
#    #e, position, velocity = tle.sgp4(jd, fr)
#    position_TEME = np.array(position)
#    #position_PEF = np.array(position)
#
#
#    ## convert to Pseudo Earth Fixed [PEF]
#
#    # compute Julian centeries of UT1 - discussed in Vallado et al., 2006, sec. II.E
#    #JD = jday2(t.year,t.month,t.day,t.hour,t.minute,t.second)
#    JD = np.array([jday2(t.year,t.month,t.day,t.hour,t.minute,t.second) for t in time0])
#
#    T_UT1 = (JD - 2451545.0)/36525.
#
#    # compute Greenwich Mean Sidereal Time (units of s) - Vallado et al., 2006, eqn. 2
#    GMST = (67310.54841+(876600*60*60+8640184.812866)*T_UT1+0.093104*T_UT1**2-6.2e-6*T_UT1**3)
#    # convert GMST to angle (units of rad)
#    GMST = GMST*2*np.pi/86400. % (2*np.pi)
#    # form rotational matrix
#    #Rot = np.array([[np.cos(GMST),np.sin(GMST),0.],[-np.sin(GMST),np.cos(GMST),0.],[0.,0.,1.]])
#    Rot = np.array([[np.cos(GMST), np.sin(GMST), np.zeros(GMST.shape)],
#                    [-np.sin(GMST), np.cos(GMST), np.zeros(GMST.shape)],
#                    [np.zeros(GMST.shape), np.zeros(GMST.shape), np.ones(GMST.shape)]])
#    # apply rotational matrix to TEME position to get PEF position (units of km) - Valladeo et al., 2006, eqn. 1
#    print(Rot.shape, position_TEME.shape)
#    #position_PEF = np.dot(Rot,position_TEME)
#    position_PEF = np.einsum('ijk,kj->ki', Rot, position_TEME)
#
#    print(position_TEME.shape, position_PEF.shape)
#
#    # add position to coordinate arrays
#    #X.append(position_PEF[0])
#    #Y.append(position_PEF[1])
#    #Z.append(position_PEF[2])
#    X = position_PEF[0]
#    Y = position_PEF[1]
#    Z = position_PEF[2]
#
#    return np.array(X)*1000., np.array(Y)*1000., np.array(Z)*1000.




def example():

    # Create a seperate file called space_track_credentials.py and add only your spacetrack credentials as shown:
    # ST_USERNAME=''
    # ST_PASSWORD=''

    # NORAD satellite ID
    #sat_id = 44628   # TLE for ICON
    sat_id = 39452

    # Create TLEHandler object
    tle = TLEHandler(sat_id)

    # Create array of desired times
    time_array = np.array([dt.datetime(2020,1,1,0,0,0)+dt.timedelta(seconds=60.*m) for m in range(60)])

    # Call tle.sat_position to calculate the satelite position at each time
    sat_position = tle.sat_position(time_array).T

    # position returned in ECEF coordinates
    print(sat_position)



###########################################################################################
# For now, assume this code is correct - confirm later once TLE lookup works for small time ranges

import matplotlib.pyplot as plt
import cartopy.crs as ccrs

def sql_test():

    sat_id = 39452   # Swarm A
    time_list = [dt.datetime(2020,2,10,13,25,0)+dt.timedelta(minutes=i) for i in range(10)]

    tlelib = TLEHandler()
    pos = tlelib.sat_position(sat_id, time_list)
    print(pos.shape)
    glat, glon, galt = pm.ecef2geodetic(pos[0], pos[1], pos[2])

    proj = ccrs.Mercator()
    fig, ax = plt.subplots(subplot_kw=dict(projection=proj))
    ax.coastlines()
    ax.gridlines()

    ax.plot(glon, glat, transform=ccrs.PlateCarree())

    plt.show()

###########################################################################################


def main():
    """
    Example where the TLE is given by user
    """

    TLE = ['1     1U          18350.30892361  .00001123  00000-0  66525-4 0   109','2     1  85.0373 178.2871 0002550 225.5672 175.5175 15.21584957    13']
    times = np.array([dt.datetime(2018,12,17,0,0,0)+dt.timedelta(hours=h) for h in range(24)])

    X, Y, Z = propagate_tle(times,TLE)
    print(X, Y, Z)
    gdlat, gdlon, gdalt = pm.ecef2geodetic(X,Y,Z)

    print('{:^20}{:^10}{:^10}{:^10}'.format('Time','GLAT','GLON','GALT'))
    for t, lat, lon, alt in zip(times,gdlat,gdlon,gdalt):
        print('{}{:10.2f}{:10.2f}{:10.2f}'.format(t, lat, lon, alt))


if __name__ == '__main__':
#    main()
#    example()
#    lib_example()
#    create_tle_library()
    #create_tle_sql()
    sql_test()
