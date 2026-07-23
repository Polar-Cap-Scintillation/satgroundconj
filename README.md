# satgroundconj
A package for determining satellite positions and calculating conjunctions with ground stations.

This package contains codes for TLE propagation using SGP4. TLEs can be retrieved from space-track.org, but the volume of TLEs required for long-term conjunction analysis violates the space-track.org API use guidelines.  Instead, a complete list of historical TLEs can be downloaded from the [space-track cloud storage site](https://ln5.sync.com/dl/afd354190/c5cd2q72-a5qjzp4q-nbjdiqkr-cenajuqu) as text files.  The satgroundconj package contains a function to convert multiple of these text files into a SQL database, which the package can then use to quickly locate the appropriate TLE to use for a particular orbit propigation.

Examples of a variety fo use cases are found in `examples.py`.
