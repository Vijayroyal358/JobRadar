from .linkedin import LinkedIn
from .naukri import Naukri
from .remote_boards import Arbeitnow, Himalayas, Jobicy, RemoteOK, Remotive, TheMuse, WeWorkRemotely

SCRAPERS = [LinkedIn, Naukri, Remotive, RemoteOK, Himalayas, Jobicy, WeWorkRemotely, Arbeitnow, TheMuse]
BY_KEY = {cls.key: cls for cls in SCRAPERS}
