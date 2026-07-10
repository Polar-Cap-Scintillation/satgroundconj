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


import numpy as np
import datetime as dt
import pymap3d as pm
#from spacetrack import SpaceTrackClient
from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv
from sgp4.ext import jday
from pathlib import Path

# import SpaceTrack username and password
#from space_track_credentials import *

#class TLEHandler(object):
#    def __init__(self, sid):
#
#        self.load_tle(sid)
#        #self.create_tle_library(sid)
#
#    def load_tle(self, sid):
#        # load TLE library for a single sattelite from local
#        # if satellite does not exist, download from spacetrack
#
#        tle_file = Path(local_tle_library, f'{sid}.txt')
#        #print(tle_file)
#
#        # parse output into list of distinct TLEs
#        try:
#            with open(tle_file, 'r') as f:
#                output = f.read()
#        except FileNotFoundError:
#            self.download_tle(sid)
#            with open(tle_file, 'r') as f:
#                output = f.read()
#
#        split = output.splitlines()
#        self.TLE_list = [[split[2*i],split[2*i+1]] for i in range(len(split)//2)]
#
#        # extract epoch from each TLE
#        # Do this as np.datetime64 instead of datetime?  May be faster?
#        self.TLE_epoch = [dt.datetime.strptime(tle[0][18:23],'%y%j')+dt.timedelta(days=float(tle[0][23:32])) for tle in self.TLE_list]
#
#    def download_tle(self, sid):
#        # retrieve all TLEs for satellite from space-track.org
#        # The space-track.org API limits the number of calls you can make, so it's better to retreive the
#        #   entire library for one satellite and save it locally than try to collect individual
#        #   TLEs as needed.
#
#        print(f'Downloading TLE for {sid} from spacetrack.org')
#        st = SpaceTrackClient(identity=ST_USERNAME, password=ST_PASSWORD, base_url='https://for-testing-only.space-track.org')
#        output = st.gp_history(norad_cat_id=sid, orderby='epoch asc', format='tle')
#
#        tle_file = Path(local_tle_library, f'{sid}.txt')
#        with open(tle_file, 'w') as f:
#            f.write(output)
#        print('...Done')
#        #print(output)
#
#
#
#    def create_tle_library(self, sid):
#        # retrieve TLEs for entire period from space-track.org
#        # The space-track.org API limits the number of calls you can make, so it's better to retreive the
#        #   entire library for one satellite and save it as a class attribute than try to collect indivitual
#        #   TLEs as needed.
#        st = SpaceTrackClient(identity=ST_USERNAME, password=ST_PASSWORD, base_url='https://for-testing-only.space-track.org')
#        output = st.gp_history(norad_cat_id=sid, orderby='epoch asc', format='tle')
#
#        print(output)
#
#        # parse output into list of distinct TLEs
#        split = output.splitlines()
#        self.TLE_list = [[split[2*i],split[2*i+1]] for i in range(len(split)//2)]
#
#        # extract epoch from each TLE
#        self.TLE_epoch = [dt.datetime.strptime(tle[0][18:23],'%y%j')+dt.timedelta(days=float(tle[0][23:32])) for tle in self.TLE_list]
#
#    def sat_position(self, time_array):
#
#        # Find index of epoch closest to each time in the time array
#        unix_time_array = np.array(time_array).astype('datetime64')
#        unix_TLE_epoch = np.array(self.TLE_epoch).astype('datetime64')
#        closest_epoch_idx = np.array([np.argmin(np.abs(ut-unix_TLE_epoch)) for ut in unix_time_array])
#
#        # Somewhere in here check that epoch is within 10 days and if not, update TLE library from spacetrack.org?
#        # Raise warning instead?
#
#        sat_position = np.empty((3,0))
#
#        for i in np.unique(closest_epoch_idx):
#            subset_times = time_array[closest_epoch_idx==i]
#
#            # calcualte satellite position using functions from TLE propgation script
#            X, Y, Z = propagate_tle(subset_times,self.TLE_list[i])
#            sat_position = np.append(sat_position, np.array([X, Y, Z]), axis=1)
#
#        return sat_position

class TLEHandler(object):
    def __init__(self, dbfile='tle.db'):
        dbfile = '/Users/e30737/Desktop/Research/PolarCapScintillation/conjunctions/tle.db'

        self.load_db(dbfile)

        #self.load_tle(sid)
        #self.create_tle_library(sid)

    def load_db(self, dbfile):

        engine = create_engine(f"sqlite:///{dbfile}", echo=False)
        #self.session = sessionmaker(bind=engine)()
        self.session = Session(engine)


    def sat_position(self, sat_cat, time_array):
        # Note: This function only works for sequential times

        #starttime = min(time_array)
        #endtime = max(time_array)
        #print(starttime, endtime)

        #utime = np.datetime64('2020-03-01T00:00:00').astype('datetime64[s]').astype('int')
        #utime = 1609178787.671904
        #utime = (dt.datetime(2020,3,1)-dt.datetime.utcfromtimestamp(0)).total_seconds()
        #ustarttime = (starttime-dt.datetime.utcfromtimestamp(0)).total_seconds()
        #uendtime = (endtime-dt.datetime.utcfromtimestamp(0)).total_seconds()
        sat_cat = int(sat_cat)

        utime_array = np.array([(t-dt.datetime.fromtimestamp(0)).total_seconds() for t in time_array])

        # Find experiment by start/end times and radar id
        conditions = sqlalchemy.and_(TLE.norad==sat_cat)
                                     #TLE.epoch<=utime)
                                     #TLE.epoch>=utime_array[0],
                                     #TLE.epoch<=utime_array[-1])

        tle_list = self.session.query(TLE).filter(conditions).order_by(TLE.epoch).all()
        # If list is empty, need to do something else?  Change time range??
        print(len(tle_list))

        #tle_list = self.session.query(TLE).filter(conditions).order_by(desc(TLE.epoch)).first()
        #tle_list = self.session.query(TLE).filter(conditions).order_by(abs(TLE.epoch-utime)).all()
        #.order_by(TLE.epoch).order_by(TLE.setnum).all()

        #print(abs(tle_list.epoch-utime)/3600.)

        epoch_list = [t.epoch for t in tle_list]
        #print(epoch_list)
        
        #print(len(tle_list))
        #for t in tle_list:
        #    print(t.epoch)
        #    print(abs(t.epoch-utime)/3600.)

        # Find index of epoch closest to each time in the time array
        #unix_time_array = np.array(time_array).astype('datetime64')
        #unix_TLE_epoch = np.array(epoch_list).astype('datetime64')
        closest_epoch_idx = np.array([np.argmin(np.abs(ut-epoch_list)) for ut in utime_array])
        #print(len(utime_array), len(epoch_list), len(closest_epoch_idx))

        ## Somewhere in here check that epoch is within 10 days and if not, update TLE library from spacetrack.org?
        ## Raise warning instead?

        sat_position = np.empty((3,0))

        for i in np.unique(closest_epoch_idx):
            #print(i)
            subset_times = np.array(time_array)[closest_epoch_idx==i]
            #print(len(subset_times))

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


#class ManageLibrary(object):
#
#    def __init__(self, libdir):
#
#        self.basedir = libdir
#
#    def load_tle(self, sid):
#        # load TLE library for a single sattelite from local
#        # if satellite does not exist, download from spacetrack
#
#        tle_file = Path(self.basedir, f'{sid}.txt')
#        print(tle_file)
#
#        # parse output into list of distinct TLEs
#        try:
#            with open(tle_file, 'r') as f:
#                output = f.read()
#        except FileNotFoundError:
#            #self.download_tle(sid)
#            with open(tle_file, 'r') as f:
#                output = f.read()
#
#        split = output.splitlines()
#        self.TLE_list = [[split[2*i],split[2*i+1]] for i in range(len(split)//2)]
#
#        # extract epoch from each TLE
#        # Do this as np.datetime64 instead of datetime?  May be faster?
#        self.TLE_epoch = [dt.datetime.strptime(tle[0][18:23],'%y%j')+dt.timedelta(days=float(tle[0][23:32])) for tle in self.TLE_list]
#
#        print(self.TLE_epoch)


import sqlalchemy
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float, DateTime, Text
#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy import UniqueConstraint
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

class TLE(Base):
    __tablename__ = 'tle'

    id = Column(Integer, primary_key = True)
    norad = Column(Integer, nullable = False)
    #epoch = Column(DateTime(), nullable=False)
    epoch = Column(Integer, nullable=False)
    line1 = Column(String(70), nullable=False)
    line2 = Column(String(70), nullable=False)
    setnum = Column(Integer, nullable=True)

from sgp4.conveniences import sat_epoch_datetime

def create_tle_sql():

    filename = '/Users/e30737/Desktop/Data/TLE/tle2020.txt'
    engine = create_engine("sqlite:///tle.db", echo=False)

    Base.metadata.create_all(engine)
    

    with Session(engine) as session:

        with open(filename, 'r') as f:
            i = 0
            for l1 in f:
                l2 = f.readline()
       
                try:
                    elm = twoline2rv(l1, l2, wgs72)
                except ValueError as e:
                    #print(e)
                    #print(len(l1), len(l2))
                    #print('LINE 1:', l1)
                    #print('LINE 2:', l2)
                    continue

                #noradid = int(l1[2:7])
                #epoch = dt.datetime.strptime(l1[18:23],'%y%j')+dt.timedelta(days=float(l1[23:32]))
                    #print(noradid, epoch)
                #except Exception as e:
                #    #print(l1)
                #    #print(e)
                #    continue

                # Error in this function??? Returns year 2020 as 3920
                #print(elm.epoch)
                #epoch = sat_epoch_datetime(elm)
                #print(epoch)
                #year = elm.epochyr
                #print(year)
                #year += 1900 + (year < 57) * 100
                #print(year)

                ut_epoch = (elm.epoch-dt.datetime.fromtimestamp(0)).total_seconds()
                
                print(i)
                element = TLE(id=i, norad=elm.satnum, epoch=ut_epoch, line1=l1, line2=l2, setnum=elm.elnum)
    
                session.add(element)
                #session.commit()
                i += 1
                
        session.commit()



def sql_test():

    sat_id = 39452
    time_list = [dt.datetime(2020,3,1)+dt.timedelta(minutes=i) for i in range(30*24*60)]

    tlelib = TLEHandler()
    tlelib.sat_position(sat_id, time_list)

    #engine = create_engine("sqlite:///tle.db", echo=False)
    ##Session = sessionmaker(bind=engine)
    ##session = Session()

    #with Session(engine) as session:
    #    tle_list = session.query(TLE).filter(TLE.norad==28254).order_by(TLE.epoch).order_by(TLE.setnum).all()
    #print(len(tle_list))

    #for t in tle_list:
    #    print(t.epoch)
    #    print(t.line1)
    #    print(t.line2)




#def create_tle_library():
#
#    sid = [55268,
#        62339]
#       
#    sid.sort()
#
#    with SpaceTrackClient(identity=ST_USERNAME, password=ST_PASSWORD, base_url='https://for-testing-only.space-track.org') as client:
#        output = client.gp_history(norad_cat_id=sid, orderby=['norad_cat_id','epoch asc'], format='tle')
#
#    for i in range(len(sid)-1):
#        part = output.partition(f'1 {sid[i+1]}U')
#    #for p in part:
#    #    print(p)
#
#        tle_file = Path(local_tle_library, f'{sid[i]}.txt')
#        with open(tle_file, 'w') as f:
#            f.write(part[0])
#        output = part[1]+part[2]
#
#    tle_file = Path(local_tle_library, f'{sid[-1]}.txt')
#    with open(tle_file, 'w') as f:
#        f.write(output)
#        #print('...Done')
#
#def lib_example():
#    local_tle_library = '/Users/e30737/Desktop/Data/TLE/'
#    lib = ManageLibrary(local_tle_library)
#
#    lib.load_tle(40730)

def main():
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
    create_tle_sql()
    #sql_test()
