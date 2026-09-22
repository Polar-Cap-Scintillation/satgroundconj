# propogate_tle.py

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

import os
import numpy as np
import datetime as dt
import pymap3d as pm
from tqdm import tqdm

from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv
from sgp4.ext import jday

import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from zipfile import ZipFile



Base = declarative_base()

class TLE(Base):
    __tablename__ = 'tle'

    id = Column(Integer, primary_key = True)
    norad = Column(Integer, nullable = False, index=True)
    epoch = Column(Integer, nullable=False)
    line1 = Column(String(70), nullable=False)
    line2 = Column(String(70), nullable=False)
    setnum = Column(Integer, nullable=True)


def create_tle_sql(source_files, dbfile='tle.db'):

    if os.path.exists(dbfile):
        raise FileExistsError(f'File {dbfile} already exists!')

    numfiles = len(source_files)

    # Source files need to be refrenced more dynamically
    engine = create_engine(f"sqlite:///{dbfile}", echo=False)

    Base.metadata.create_all(engine)
    
    with Session(engine) as session:

        i = 0       # unique id counter
        for fi, srcfile in enumerate(source_files):
            print(f'[{fi+1}/{numfiles}] {srcfile}')

#            with ZipFile(srcfile) as zf:
#
#                for filename in zf.namelist():
#                    print(f'{filename} in {srcfile}')
#
            with open(srcfile, 'r') as f:
                num_lines = sum(1 for line in f)
 
            with open(srcfile, 'r') as f:
                for l1 in tqdm(f, total=num_lines/2):
                    l2 = f.readline()
           
                    try:
                        elm = twoline2rv(l1, l2, wgs72)
                    except ValueError as e:
                        # Put this in an error log
                        #print(e)
                        #print(len(l1), len(l2))
                        #print('LINE 1:', l1)
                        #print('LINE 2:', l2)
                        continue
    
                    ut_epoch = (elm.epoch-dt.datetime.fromtimestamp(0)).total_seconds()
                    
                    element = TLE(id=i, norad=elm.satnum, epoch=ut_epoch, line1=l1, line2=l2, setnum=elm.elnum)
        
                    session.add(element)
                    i += 1

            print('Committing to SQL database ...')
            session.commit()




class TLEHandler(object):
    def __init__(self, dbfile='tle.db'):

        self.load_db(dbfile)


    def load_db(self, dbfile):

        engine = create_engine(f"sqlite:///{dbfile}", echo=False)
        self.session = Session(engine)

    def select_tles(self, sat_cat, time0, time1):

        sat_cat = int(sat_cat)
        utime0 = (time0-dt.datetime.fromtimestamp(0)).total_seconds()
        utime1 = (time1-dt.datetime.fromtimestamp(0)).total_seconds()
        #utime_array = np.array([(t-dt.datetime.fromtimestamp(0)).total_seconds() for t in time_array])

        # Make this its own function??
        # Extract relevant TLEs from database
        # There might be a more elegant way to do this if you're better at SQL, but this works

        # All TLEs between first and last time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                     TLE.epoch>=utime0,
                                     TLE.epoch<=utime1)
        tle_between = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).all()

        # Last epoch before first time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                      TLE.epoch<utime0)
        tle_first = self.session.query(TLE).filter(conditions).order_by(desc(TLE.epoch)).first()

        # First epoch after last time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                      TLE.epoch>utime1)
        tle_last = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).first()

        # Create full list
        tle_list = [tle_first] + tle_between + [tle_last]

        # Extract array of epoch times
        epoch_list = [t.epoch for t in tle_list]

        return epoch_list


    def sat_position(self, sat_cat, time_array):
        # Note: This function only works for sequential times

        sat_cat = int(sat_cat)
        utime_array = np.array([(t-dt.datetime.fromtimestamp(0)).total_seconds() for t in time_array])

        # Make this its own function??
        # Extract relevant TLEs from database
        # There might be a more elegant way to do this if you're better at SQL, but this works

        # All TLEs between first and last time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                     TLE.epoch>=utime_array[0],
                                     TLE.epoch<=utime_array[-1])
        tle_between = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).all()

        # Last epoch before first time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                      TLE.epoch<utime_array[0])
        tle_first = self.session.query(TLE).filter(conditions).order_by(desc(TLE.epoch)).first()

        # First epoch after last time
        conditions = sqlalchemy.and_(TLE.norad==sat_cat,
                                      TLE.epoch>utime_array[-1])
        tle_last = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).first()

        # Create full list
        tle_list = [tle_first] + tle_between + [tle_last]

        # Extract array of epoch times
        epoch_list = [t.epoch for t in tle_list]

        # Find index of epoch closest to each time in the time array
        closest_epoch_idx = np.array([np.argmin(np.abs(ut-epoch_list)) for ut in utime_array])

        ## Somewhere in here check that epoch is within 10 days and if not, update TLE library from spacetrack.org?
        ## Raise warning instead?

        # Cycle through epochs and calculate position for satellite for each one when that epoch is the closest time
        sat_position = np.empty((3,0))

        for i in np.unique(closest_epoch_idx):
            # Select subset of times closest to a particular epoch
            subset_times = np.array(time_array)[closest_epoch_idx==i]

            # calcualte satellite position using functions from TLE propgation script
            X, Y, Z = propagate_tle(subset_times, [tle_list[i].line1, tle_list[i].line2])
            sat_position = np.append(sat_position, np.array([X, Y, Z]), axis=1)

        return sat_position


def propagate_tle(time0, TLE):
    # time0 is an array of datetime objects that the satellite position is to be calculated at
    # TLE is a list consisting of the first and second lines of the TLE as strings ([TLE line 1, TLE line 2])

    # Note: This function returns satellite position in Pseudo Earth-Fixed (PEF) coordinates, which are
    #   assumed to be approximately equal to Earth-Centered, Earth-Fixed (ECEF) coordinates.  This does NOT
    #   account for polar motion (precession, nutation).  For discussion of a "proper" PEF->ECEF transformation,
    #   please refer to Vallado et al., 2006 Appendix C or Panigrahi and Gaurav, 2015
    #   (https://mycoordinates.org/tracking-satellite-footprints-on-earth%E2%80%99s-surface/)

    X = []
    Y = []
    Z = []

    # initialize tle object
    tle = twoline2rv(TLE[0],TLE[1],wgs72)

    for t in time0:

        # calculate satellite position/velocity in True Equator, Mean Equinox [TEME] (units of km and km/s)
        position, velocity = tle.propagate(t.year,month=t.month,day=t.day,hour=t.hour,minute=t.minute,second=t.second)
        position_TEME = np.array(position)


        # convert to Pseudo Earth Fixed [PEF]

        # compute Julian centeries of UT1 - discussed in Vallado et al., 2006, sec. II.E
        JD = jday(t.year,t.month,t.day,t.hour,t.minute,t.second)
        T_UT1 = (JD - 2451545.0)/36525.

        # compute Greenwich Mean Sidereal Time (units of s) - Vallado et al., 2006, eqn. 2
        GMST = (67310.54841+(876600*60*60+8640184.812866)*T_UT1+0.093104*T_UT1**2-6.2e-6*T_UT1**3)
        # convert GMST to angle (units of rad)
        GMST = GMST*2*np.pi/86400. % (2*np.pi)
        # form rotational matrix
        Rot = np.array([[np.cos(GMST),np.sin(GMST),0.],[-np.sin(GMST),np.cos(GMST),0.],[0.,0.,1.]])
        # apply rotational matrix to TEME position to get PEF position (units of km) - Valladeo et al., 2006, eqn. 1
        position_PEF = np.dot(Rot,position_TEME)

        # add position to coordinate arrays
        X.append(position_PEF[0])
        Y.append(position_PEF[1])
        Z.append(position_PEF[2])

    return np.array(X)*1000., np.array(Y)*1000., np.array(Z)*1000.




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
