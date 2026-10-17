"""Skill taxonomy and skill detection.

Each canonical skill maps to a list of aliases. Aliases match case-insensitively on word
boundaries. Prefix an alias with "re:" for a raw case-insensitive regex, or "cs:" for a raw
case-sensitive regex. Users can also add their own skills; those are matched literally.
"""
import re
from functools import lru_cache

TAXONOMY = {
    "Languages": {
        "Python": ["python", "python3"],
        "Java": ["java", "core java", "j2ee", "java ee", "jdk"],
        "JavaScript": ["javascript", "java script", "es6", "ecmascript"],
        "TypeScript": ["typescript"],
        "C": ["c programming", "c language", "embedded c", "ansi c",
              r"re:(?<![a-z0-9+#])c(?=\s*(?:/|,|and|&)\s*c\+\+)"],
        "C++": ["c++", "cpp", "c plus plus", "stl"],
        "C#": ["c#", "c sharp", "csharp"],
        "Go": ["golang", "go lang", r"re:\bgo\s*(?:developer|engineer|programming|language)\b"],
        "Rust": ["rust"],
        "Kotlin": ["kotlin"],
        "Swift": ["swift"],
        "Objective-C": ["objective-c", "objective c"],
        "PHP": ["php"],
        "Ruby": ["ruby"],
        "Scala": ["scala"],
        "R": ["r programming", "r language", "rstudio",
              r"cs:(?<![A-Za-z0-9])R(?=\s*(?:,|/|and\b|programming|language|studio))"],
        "MATLAB": ["matlab", "simulink"],
        "Perl": ["perl"],
        "Shell Scripting": ["shell scripting", "shell script", "bash", "bash scripting", "unix shell", "ksh", "zsh"],
        "PowerShell": ["powershell", "power shell"],
        "SQL": ["sql", "t-sql", "tsql", "pl/sql", "plsql", "pl-sql"],
        "Dart": ["dart"],
        "Groovy": ["groovy"],
        "VBA": ["vba", "excel macros"],
        "Assembly": ["assembly language", "assembly"],
        "Elixir": ["elixir"],
        "Haskell": ["haskell"],
        "Lua": ["lua"],
        "Solidity": ["solidity"],
        "COBOL": ["cobol"],
        "ABAP": ["abap"],
        "Verilog": ["verilog", "systemverilog", "system verilog"],
        "VHDL": ["vhdl"],
    },
    "Web & Frontend": {
        "React": ["react", "react.js", "reactjs", "react js"],
        "Angular": ["angular", "angularjs", "angular.js"],
        "Vue.js": ["vue", "vue.js", "vuejs"],
        "Next.js": ["next.js", "nextjs"],
        "Nuxt": ["nuxt", "nuxt.js"],
        "Svelte": ["svelte", "sveltekit"],
        "Redux": ["redux"],
        "HTML": ["html", "html5"],
        "CSS": ["css", "css3", "scss", "sass"],
        "Tailwind CSS": ["tailwind", "tailwindcss"],
        "Bootstrap": ["bootstrap"],
        "jQuery": ["jquery"],
        "Webpack": ["webpack", "vite", "babel"],
        "React Native": ["react native", "react-native"],
        "Flutter": ["flutter"],
        "Ionic": ["ionic"],
        "Web Accessibility": ["accessibility", "wcag", "a11y"],
        "GraphQL": ["graphql", "apollo"],
        "WebSockets": ["websocket", "websockets", "socket.io"],
        "Figma": ["figma"],
        "UI/UX Design": ["ui/ux", "ux design", "ui design", "wireframing", "prototyping"],
    },
    "Backend & Frameworks": {
        "Node.js": ["node.js", "nodejs", "node js", "node"],
        "Express.js": ["express.js", "expressjs", "express"],
        "NestJS": ["nestjs", "nest.js"],
        "Django": ["django", "django rest framework", "drf"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi", "fast api"],
        "Spring Boot": ["spring boot", "springboot", "spring framework", "spring mvc", "spring cloud", "spring"],
        "Hibernate": ["hibernate", "jpa"],
        ".NET": [".net", "dotnet", ".net core", "asp.net", "asp.net core", "entity framework"],
        "Ruby on Rails": ["ruby on rails", "rails", "ror"],
        "Laravel": ["laravel"],
        "Microservices": ["microservices", "micro services", "microservice"],
        "REST APIs": ["rest api", "rest apis", "restful", "restful apis", "web services", "api development", "rest"],
        "gRPC": ["grpc", "protobuf", "protocol buffers"],
        "SOAP": ["soap"],
        "Kafka": ["kafka", "apache kafka", "confluent"],
        "RabbitMQ": ["rabbitmq", "rabbit mq", "amqp"],
        "Celery": ["celery"],
        "Redis": ["redis"],
        "Elasticsearch": ["elasticsearch", "elastic search", "opensearch", "elk", "elk stack"],
        "System Design": ["system design", "distributed systems", "scalable systems", "high availability"],
        "Design Patterns": ["design patterns", "solid principles", "oop", "oops", "object oriented", "object-oriented"],
        "Data Structures & Algorithms": ["data structures", "algorithms", "dsa"],
        "Multithreading": ["multithreading", "multi-threading", "concurrency", "multithreaded"],
        "Linux Kernel": ["linux kernel", "kernel development", "device drivers", "device driver"],
    },
    "Databases": {
        "MySQL": ["mysql", "mariadb"],
        "PostgreSQL": ["postgresql", "postgres"],
        "Oracle DB": ["oracle database", "oracle db", "oracle 19c", "oracle"],
        "SQL Server": ["sql server", "mssql", "ms sql", "ssms"],
        "MongoDB": ["mongodb", "mongo db", "mongo"],
        "Cassandra": ["cassandra"],
        "DynamoDB": ["dynamodb", "dynamo db"],
        "SQLite": ["sqlite"],
        "Neo4j": ["neo4j", "graph database"],
        "Snowflake": ["snowflake"],
        "BigQuery": ["bigquery", "big query"],
        "Redshift": ["redshift"],
        "NoSQL": ["nosql", "no-sql"],
        "Database Administration": ["database administration", "database administrator", "dba"],
    },
    "Cloud & DevOps": {
        "AWS": ["aws", "amazon web services", "ec2", "s3", "cloudformation", "eks", "aws lambda", "lambda"],
        "Azure": ["azure", "microsoft azure", "azure devops", "aks", "azure functions"],
        "GCP": ["gcp", "google cloud", "google cloud platform", "gke"],
        "Docker": ["docker", "containerization", "dockerfile", "containers"],
        "Kubernetes": ["kubernetes", "k8s", "openshift", "helm"],
        "Terraform": ["terraform", "infrastructure as code", "iac"],
        "Ansible": ["ansible"],
        "Puppet/Chef": ["puppet", "chef"],
        "Jenkins": ["jenkins"],
        "CI/CD": ["ci/cd", "ci cd", "cicd", "continuous integration", "continuous delivery", "continuous deployment",
                  "github actions", "gitlab ci", "bamboo", "teamcity", "circleci", "argo cd", "argocd"],
        "Git": ["git", "github", "gitlab", "bitbucket", "version control"],
        "SVN": ["svn", "subversion"],
        "Linux": ["linux", "unix", "ubuntu", "centos", "rhel", "red hat", "redhat", "debian"],
        "Linux Administration": ["linux administration", "linux admin", "linux system administration", "rhcsa", "rhce"],
        "Prometheus": ["prometheus"],
        "Grafana": ["grafana"],
        "Monitoring & Observability": ["observability", "datadog", "new relic", "nagios", "zabbix", "dynatrace",
                                       "appdynamics", "monitoring tools", "monitoring"],
        "Splunk": ["splunk"],
        "Web Servers": ["nginx", "apache http", "httpd", "tomcat", "iis"],
        "SRE": ["site reliability", "sre"],
        "Serverless": ["serverless"],
        "Cloud Computing": ["cloud computing", "cloud infrastructure", "cloud native", "cloud-native"],
        "VMware": ["vmware", "vsphere", "esxi", "vcenter"],
        "Hyper-V": ["hyper-v", "hyperv"],
        "Virtualization": ["virtualization", "virtualisation", "kvm", "virtual machines"],
        "OpenStack": ["openstack"],
        "Maven/Gradle": ["maven", "gradle", "ant"],
        "Build Systems": ["cmake", "makefile", "bazel", "yocto", "buildroot", "make"],
    },
    "Data & AI": {
        "Machine Learning": ["machine learning", "ml models", "ml algorithms", "supervised learning", "unsupervised learning"],
        "Deep Learning": ["deep learning", "neural networks", "neural network", "cnn", "rnn", "lstm"],
        "NLP": ["nlp", "natural language processing", "text mining"],
        "Computer Vision": ["computer vision", "opencv", "image processing"],
        "Generative AI": ["generative ai", "genai", "gen ai", "llm", "llms", "large language models", "rag",
                          "prompt engineering", "langchain", "llamaindex", "openai", "gpt", "vector database", "ai agents"],
        "TensorFlow": ["tensorflow", "keras"],
        "PyTorch": ["pytorch", "torch"],
        "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
        "Pandas": ["pandas"],
        "NumPy": ["numpy", "scipy"],
        "Data Analysis": ["data analysis", "data analytics", "exploratory data analysis", "eda"],
        "Data Visualization": ["data visualization", "data visualisation", "matplotlib", "seaborn", "plotly", "dashboards"],
        "Statistics": ["statistics", "statistical analysis", "hypothesis testing", "regression analysis", "a/b testing"],
        "Power BI": ["power bi", "powerbi", "dax", "power query"],
        "Tableau": ["tableau"],
        "Excel": ["excel", "ms excel", "microsoft excel", "advanced excel", "vlookup", "pivot tables", "pivot table", "excel reporting"],
        "Apache Spark": ["pyspark", "apache spark", "spark sql", "spark"],
        "Hadoop": ["hadoop", "hdfs", "hive", "mapreduce", "hbase"],
        "Airflow": ["airflow", "apache airflow"],
        "ETL": ["etl", "elt", "data pipelines", "data pipeline", "informatica", "talend", "ssis", "data integration"],
        "Databricks": ["databricks", "delta lake"],
        "dbt": ["dbt"],
        "Data Warehousing": ["data warehouse", "data warehousing", "dwh", "data modeling", "data modelling", "star schema"],
        "MLOps": ["mlops", "mlflow", "kubeflow", "sagemaker", "model deployment"],
        "Big Data": ["big data"],
    },
    "Testing & QA": {
        "Selenium": ["selenium", "selenium webdriver", "webdriver"],
        "Cypress": ["cypress"],
        "Playwright": ["playwright"],
        "Appium": ["appium"],
        "TestNG/JUnit": ["testng", "junit", "nunit", "mockito"],
        "PyTest": ["pytest", "unittest"],
        "Robot Framework": ["robot framework"],
        "Cucumber/BDD": ["cucumber", "bdd", "gherkin", "behave", "specflow"],
        "Test Automation": ["test automation", "automation testing", "automated testing", "automation framework", "sdet"],
        "Manual Testing": ["manual testing", "functional testing", "regression testing", "test cases", "test case design",
                           "test plan", "test plans", "smoke testing", "sanity testing", "uat", "black box testing"],
        "API Testing": ["api testing", "postman", "rest assured", "rest-assured", "soapui"],
        "Performance Testing": ["performance testing", "load testing", "jmeter", "loadrunner", "gatling", "locust"],
        "Unit Testing": ["unit testing", "unit tests", "tdd", "test driven development", "jest", "mocha", "jasmine"],
        "Defect Tracking": ["defect tracking", "bug tracking", "defect management", "bugzilla"],
        "Mobile Testing": ["mobile testing"],
        "ISTQB": ["istqb"],
    },
    "IT Infrastructure & Support": {
        "Windows Server": ["windows server", "windows server 2016", "windows server 2019", "windows server 2022"],
        "Active Directory": ["active directory", "ad ds", "group policy", "gpo", "ldap"],
        "Azure AD / Entra ID": ["azure ad", "azure active directory", "entra id", "entra"],
        "Microsoft 365": ["office 365", "o365", "microsoft 365", "m365", "exchange online", "exchange server", "sharepoint",
                          "teams administration"],
        "Intune / MDM": ["intune", "mdm", "mobile device management", "endpoint manager", "jamf", "airwatch", "workspace one"],
        "SCCM": ["sccm", "mecm", "configuration manager"],
        "IT Support": ["it support", "technical support", "desktop support", "help desk", "helpdesk", "service desk",
                       "end user support", "l1 support", "l2 support", "l3 support", "first level support"],
        "Troubleshooting": ["troubleshooting", "troubleshoot", "root cause analysis", "rca"],
        "ITIL": ["itil", "incident management", "problem management", "itsm"],
        "ServiceNow": ["servicenow", "service now"],
        "Ticketing Tools": ["ticketing tool", "ticketing system", "zendesk", "freshdesk", "bmc remedy", "remedy",
                            "jira service management", "manageengine", "ticketing"],
        "Hardware Support": ["hardware troubleshooting", "hardware support", "laptops", "desktops", "printers", "peripherals"],
        "OS Installation & Patching": ["os installation", "os deployment", "windows deployment", "wds", "mdt",
                                      "patch management", "patching", "imaging"],
        "Backup & Recovery": ["disaster recovery", "veeam", "commvault", "backup and recovery", "backup"],
        "IT Asset Management": ["it asset management", "asset management", "itam"],
        "Windows": ["windows 10", "windows 11", "windows os", "windows"],
        "macOS": ["macos", "mac os", "os x"],
        "Citrix / VDI": ["citrix", "vdi", "virtual desktop"],
        "Storage": ["netapp", "storage administration", "san", "nas"],
        "Remote Support Tools": ["remote desktop", "rdp", "teamviewer", "anydesk"],
        "Email Administration": ["email administration", "mail server", "smtp", "exchange"],
        "RMM Tools": ["kaseya", "rmm", "connectwise", "n-able", "ninjaone"],
    },
    "Networking": {
        "TCP/IP": ["tcp/ip", "tcp", "udp", "ip addressing", "subnetting", "ipv4", "ipv6", "osi model"],
        "DNS/DHCP": ["dns", "dhcp"],
        "Routing & Switching": ["routing and switching", "routing & switching", "vlan", "vlans", "lan/wan", "lan", "wan",
                                "routing", "switching", "stp"],
        "Routing Protocols": ["bgp", "ospf", "eigrp", "is-is", "mpls", "rip"],
        "Cisco": ["cisco", "cisco ios", "nexus", "catalyst", "meraki"],
        "Juniper": ["juniper", "junos"],
        "CCNA": ["ccna"],
        "CCNP": ["ccnp", "ccie"],
        "Firewalls": ["firewall", "firewalls", "palo alto", "fortinet", "fortigate", "checkpoint", "check point", "sophos", "asa"],
        "VPN": ["vpn", "ipsec", "ssl vpn", "site-to-site"],
        "Wireless Networking": ["wifi", "wi-fi", "wlan", "aruba", "802.11", "wireless"],
        "SD-WAN": ["sd-wan", "sdwan"],
        "Network Security": ["network security", "ids/ips", "ips", "ids", "nac"],
        "Network Monitoring": ["network monitoring", "solarwinds", "prtg", "wireshark", "packet analysis", "snmp", "netflow"],
        "Load Balancers": ["load balancer", "load balancing", "f5", "big-ip", "netscaler"],
        "Network Automation": ["network automation", "netmiko", "napalm", "netconf", "yang"],
        "SDN/NFV": ["sdn", "nfv", "vnf", "cnf"],
    },
    "Security": {
        "Cybersecurity": ["cybersecurity", "cyber security", "information security", "infosec"],
        "SIEM": ["siem", "qradar", "arcsight", "microsoft sentinel", "logrhythm"],
        "SOC": ["security operations", "soc analyst", "security operations center", "soc"],
        "Vulnerability Management": ["vulnerability assessment", "vulnerability management", "nessus", "qualys", "vapt", "rapid7"],
        "Penetration Testing": ["penetration testing", "pen testing", "pentesting", "ethical hacking", "burp suite",
                                "metasploit", "kali linux"],
        "IAM": ["identity and access management", "okta", "saml", "oauth", "single sign-on", "cyberark", "iam", "sso", "pam"],
        "Endpoint Security": ["endpoint security", "edr", "xdr", "crowdstrike", "antivirus", "sentinelone", "symantec"],
        "Cloud Security": ["cloud security", "cspm", "casb"],
        "Compliance": ["iso 27001", "soc 2", "soc2", "gdpr", "hipaa", "pci dss", "pci-dss", "nist", "compliance", "audit"],
        "Cryptography": ["cryptography", "encryption", "pki", "ssl/tls", "tls", "ssl"],
        "DevSecOps": ["devsecops", "sast", "dast", "sonarqube", "snyk"],
        "Security Certifications": ["cissp", "cism", "security+", "comptia security", "oscp", "ceh"],
    },
    "Telecom & Wireless": {
        "LTE/4G": ["lte", "4g", "eutran", "e-utran", "enodeb", "enb", "epc"],
        "5G NR": ["5g", "5g nr", "gnodeb", "gnb", "5gc", "5g core", r"cs:\bNR\b"],
        "2G/3G": ["gsm", "umts", "wcdma", "2g", "3g", "gprs", "bsc", "rnc"],
        "RAN": ["radio access network", "vran", "cloud ran", "c-ran", r"cs:(?<![-\w])v?RAN\b"],
        "O-RAN": ["o-ran", "oran", "open ran", "openran", "near-rt ric", "xapp", "rapp", r"cs:\bRIC\b"],
        "3GPP": ["3gpp"],
        "Telecom Protocols": ["diameter", "ss7", "sctp", "gtp", "s1ap", "ngap", "x2ap", "f1ap", "e1ap", "rrc", "pdcp", "rlc",
                              "mac layer", "sip"],
        "IMS/VoLTE": ["volte", "vonr", "voip", "ims"],
        "RF Engineering": ["rf planning", "rf optimization", "rf optimisation", "drive test", "antenna", "atoll", r"cs:\bRF\b"],
        "Small Cells": ["small cell", "small cells", "femtocell"],
        "Fronthaul/CPRI": ["cpri", "ecpri", "fronthaul", "split 7.2"],
        "Packet Core": ["packet core", "mme", "sgw", "pgw", "amf", "smf", "upf"],
        "Telecom OSS/BSS": ["oss/bss", "ems", "nms", "oam", "oss", "bss"],
        "PHY/DSP": ["physical layer", "baseband", "ofdm", "mimo", "dsp", "phy"],
        "DPDK": ["dpdk", "sr-iov"],
        "IoT": ["iot", "internet of things", "mqtt", "zigbee", "lorawan"],
    },
    "Embedded & Hardware": {
        "Embedded Systems": ["embedded systems", "embedded software", "firmware", "embedded linux"],
        "RTOS": ["rtos", "freertos", "vxworks", "zephyr", "threadx"],
        "Microcontrollers": ["microcontroller", "microcontrollers", "arm cortex", "stm32", "arduino", "esp32", "pic", "avr"],
        "Communication Protocols": ["i2c", "spi", "uart", "can bus", "modbus", "pcie", "usb", "ethernet", "can"],
        "FPGA": ["fpga", "xilinx", "altera", "vivado"],
        "Raspberry Pi": ["raspberry pi"],
        "Debugging Tools": ["gdb", "jtag", "oscilloscope", "logic analyzer", "valgrind"],
        "PCB Design": ["pcb design", "altium", "orcad", "kicad"],
    },
    "Enterprise Platforms": {
        "Salesforce": ["salesforce", "apex", "visualforce", "lightning web components", "lwc", "sfdc"],
        "SAP": ["sap hana", "s/4hana", "sap fico", "sap mm", "sap sd", "sap basis", r"cs:\bSAP\b"],
        "Oracle ERP": ["oracle ebs", "oracle fusion", "oracle erp"],
        "Dynamics 365": ["dynamics 365", "dynamics crm", "d365"],
        "Workday": ["workday"],
        "Power Platform": ["power apps", "powerapps", "power automate", "power platform"],
        "RPA": ["uipath", "automation anywhere", "blue prism", "rpa"],
        "Mainframe": ["mainframe", "jcl", "cics", "db2", "z/os"],
        "CMS / E-commerce": ["wordpress", "shopify", "magento", "drupal"],
    },
    "Process & Management": {
        "Agile": ["agile", "agile methodology", "kanban"],
        "Scrum": ["scrum", "scrum master", "sprint planning"],
        "Jira": ["jira", "confluence", "atlassian"],
        "Project Management": ["project management", "program management", "pmp", "prince2", "ms project"],
        "Stakeholder Management": ["stakeholder management", "stakeholder communication", "stakeholder coordination",
                                   "client management", "client facing", "customer facing"],
        "Team Leadership": ["team leadership", "people management", "mentoring", "team management", "leading teams", "team lead"],
        "Requirements Gathering": ["requirements gathering", "requirement analysis", "requirements analysis",
                                   "business analysis", "user stories", "brd", "frd"],
        "Product Management": ["product management", "product roadmap"],
        "SDLC": ["sdlc", "software development life cycle", "stlc", "waterfall"],
        "Technical Documentation": ["technical documentation", "technical writing", "sops", "documentation"],
        "Vendor Management": ["vendor management", "vendor coordination"],
        "Release Management": ["release management", "release engineering"],
        "Six Sigma / Lean": ["six sigma", "lean six sigma", "kaizen"],
    },
    "Human Resources & Talent": {
        "Human Resources (HR)": ["human resources", "hr operations", "human resource management", "generalist hr", "hr generalist", "hrbp", "hr business partner", r"cs:\bHR\b"],
        "Learning & Development (L&D)": ["learning & development", "learning and development", "employee development", "training & development", "training and development", "l&d operations", r"re:\bl[&/]d\b", r"cs:\bL&D\b"],
        "Training Coordination": ["training coordination", "training and logistics coordination", "training logistics", "training coordinator", "training administration", "training programs", "training schedules"],
        "Training Needs Analysis (TNA)": ["training need analysis", "training needs analysis", "training need analysis (tna)", "training needs analysis (tna)", r"cs:\bTNA\b"],
        "Skill Gap Analysis": ["skill gap analysis", "skills gap analysis", "competency mapping"],
        "Training Calendar Design": ["training calendar design", "training calendar", "training curriculum"],
        "LMS Administration": ["lms administration", "learning management system", "moodle", "cornerstone", "canvas lms", "blackboard", r"cs:\bLMS\b"],
        "Employee Onboarding / Induction": ["employee onboarding", "induction", "onboarding", "new hire orientation", "e-induction", "new joiners induction"],
        "Learning Effectiveness": ["learning effectiveness", "training evaluation", "training effectiveness", "kirkpatrick model"],
        "Recruitment & Talent Acquisition": ["recruitment & selection", "recruitment and selection", "talent acquisition", "sourcing", "screening", "interviewing", "talent sourcing", "headhunting", "recruitment"],
        "Performance Management": ["performance management", "performance appraisal", "kpis", "okrs", "appraisals", "kpi"],
        "Employee Engagement": ["employee engagement", "employee relations", "employee retention"],
        "HR Operations": ["hr operations", "people operations", "hr administration", "backend hr"],
        "HRIS / HRMS": ["hris", "hrms", "workday hcm", "bamboohr", "successfactors", "peoplesoft", "darwinbox", "keka"],
        "Payroll Administration": ["payroll", "payroll processing", "compensation & benefits", "comp & ben"],
        "Labor Law & Compliance": ["labor law", "labour laws", "statutory compliance", "pf", "esi", "gratuity"],
    },
    "Operations & Administration": {
        "Administration": ["administration", "administrative support", "office administration", "facilities management"],
        "Operations Management": ["operations management", "business operations", "operations executive", "backend operations", "process operations"],
        "MIS Reporting": ["mis reporting", "training mis", "mis reports", "mis report", "management information systems", "training mis and documentation", "mis and documentation", r"cs:\bMIS\b"],
        "Process Adherence / SOP": ["sop", "sops", "process adherence", "process discipline", "standard operating procedures", r"cs:\bSOP\b", r"cs:\bSOPs\b"],
        "Banking Operations": ["banking operations", "backend banking", "backend banking operations", "transaction processing", "financial services process", "banking sector", "case handling", "reconciliation"],
        "Quality Checks & Auditing": ["quality checks", "data verification", "quality audit", "quality assurance operations"],
    },
    "Office & Productivity Tools": {
        "Microsoft Word": ["ms word", "microsoft word", "word processing"],
        "Microsoft Office": ["ms office", "microsoft office", "office 365", "m365"],
        "Microsoft PowerPoint": ["powerpoint", "ms powerpoint", "power point", "presentation design"],
        "Google Workspace": ["google docs", "google sheets", "google slides", "g suite"],
    },
    "Professional & Soft Skills": {
        "Interpersonal Skills": ["interpersonal skills", "interpersonal communication"],
        "Teamwork & Collaboration": ["teamwork", "collaboration", "cross-functional collaboration", "team player"],
        "Communication Skills": ["communication skills", "verbal communication", "written communication"],
        "Problem Solving": ["problem solving", "analytical skills", "critical thinking"],
        "Time Management": ["time management", "prioritization", "multitasking"],
        "Customer Service": ["customer service", "customer support", "client service"],
    },
}

# Aliases too generic to trust in free JD/resume text. They still count in explicit tag lists.
FREE_TEXT_BLOCK = {
    "node", "express", "rest", "spring", "oracle", "can", "pic", "avr", "san", "nas", "ims", "sip", "oss", "bss",
    "make", "ant", "ror", "asa", "ips", "ids", "nac", "rip", "stp", "routing", "switching", "lan", "wan",
    "windows", "monitoring", "documentation", "compliance", "audit", "backup", "imaging", "patching", "assembly",
    "pam", "chef", "containers", "wireless", "ticketing", "exchange", "entra", "usb", "ethernet", "phy", "dsp",
    "algorithms", "lambda", "spark", "mongo", "torch", "team lead", "mentoring", "remedy", "laptops", "desktops",
    "printers", "peripherals", "antenna", "gpt", "dashboards", "concurrency", "soc", "apollo", "rails", "behave",
    "oops", "spi", "ems", "go", "r", "c", "ran", "sap", "swift", "dart", "rust", "nms", "oam", "eda", "f5", "iis", "make", "apex", "hive", "audit", "rag",
}

# Suggested job titles, derived from which of these skills a person has.
ROLE_HINTS = {
    "Python Developer": ["Python", "Django", "Flask", "FastAPI", "REST APIs"],
    "Java Developer": ["Java", "Spring Boot", "Hibernate", "Microservices"],
    "Full Stack Developer": ["React", "Angular", "Node.js", "JavaScript", "TypeScript", "REST APIs"],
    "Frontend Developer": ["React", "Angular", "Vue.js", "TypeScript", "JavaScript", "CSS", "HTML"],
    "Backend Developer": ["Node.js", "Java", "Python", "Go", "Microservices", "REST APIs", "PostgreSQL"],
    ".NET Developer": ["C#", ".NET"],
    "C++ Developer": ["C++", "Multithreading", "Linux"],
    "Embedded Software Engineer": ["C", "C++", "Embedded Systems", "RTOS", "Microcontrollers", "Communication Protocols"],
    "DevOps Engineer": ["Docker", "Kubernetes", "Jenkins", "CI/CD", "Terraform", "Ansible", "AWS", "Azure"],
    "Cloud Engineer": ["AWS", "Azure", "GCP", "Terraform", "Cloud Computing"],
    "Site Reliability Engineer": ["SRE", "Kubernetes", "Prometheus", "Grafana", "Monitoring & Observability", "Linux"],
    "Data Engineer": ["Apache Spark", "Airflow", "Kafka", "ETL", "Databricks", "Snowflake", "Data Warehousing", "SQL"],
    "Data Analyst": ["SQL", "Excel", "Power BI", "Tableau", "Data Analysis", "Data Visualization"],
    "Data Scientist": ["Machine Learning", "Statistics", "Pandas", "scikit-learn", "Python", "Deep Learning"],
    "Machine Learning Engineer": ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "MLOps", "Generative AI"],
    "QA Automation Engineer": ["Selenium", "Cypress", "Playwright", "Test Automation", "TestNG/JUnit", "PyTest", "API Testing"],
    "QA Engineer": ["Manual Testing", "API Testing", "Defect Tracking", "Jira", "SDLC"],
    "System Administrator": ["Linux Administration", "Windows Server", "Active Directory", "VMware", "Virtualization"],
    "Network Engineer": ["Cisco", "Routing & Switching", "Routing Protocols", "CCNA", "Firewalls", "TCP/IP"],
    "IT Support Engineer": ["IT Support", "Troubleshooting", "Active Directory", "Microsoft 365", "ITIL",
                            "Ticketing Tools", "Windows"],
    "IT Administrator": ["Microsoft 365", "Active Directory", "Intune / MDM", "Windows Server", "Azure AD / Entra ID"],
    "Security Analyst": ["SIEM", "SOC", "Vulnerability Management", "Cybersecurity", "Endpoint Security"],
    "Security Engineer": ["Cybersecurity", "Penetration Testing", "IAM", "Cloud Security", "DevSecOps"],
    "Telecom Software Engineer": ["LTE/4G", "5G NR", "3GPP", "Telecom Protocols", "RAN", "C++"],
    "RAN Engineer": ["RAN", "LTE/4G", "5G NR", "O-RAN", "RF Engineering"],
    "Android Developer": ["Kotlin", "Java", "Flutter"],
    "iOS Developer": ["Swift", "Objective-C"],
    "Mobile Developer": ["React Native", "Flutter", "Kotlin", "Swift"],
    "Salesforce Developer": ["Salesforce"],
    "SAP Consultant": ["SAP"],
    "Project Manager": ["Project Management", "Agile", "Scrum", "Stakeholder Management"],
    "Business Analyst": ["Requirements Gathering", "SQL", "Excel", "Stakeholder Management"],
    "Scrum Master": ["Scrum", "Agile", "Jira"],
    "HR Specialist": ["Human Resources (HR)", "HR Operations", "Employee Onboarding / Induction", "HRIS / HRMS"],
    "L&D Specialist / Coordinator": ["Learning & Development (L&D)", "Training Coordination", "Training Needs Analysis (TNA)", "LMS Administration"],
    "Talent Acquisition Specialist": ["Recruitment & Talent Acquisition", "HR Operations", "Communication Skills"],
    "Operations Executive": ["Operations Management", "Banking Operations", "MIS Reporting", "Process Adherence / SOP", "Excel"],
    "Administrative Coordinator": ["Administration", "Vendor Management", "Microsoft Office", "Microsoft Word"],
}

SKILL_CATEGORY = {s: cat for cat, d in TAXONOMY.items() for s in d}
ALL_SKILLS = list(SKILL_CATEGORY)
_CANON_LOWER = {s.lower(): s for s in ALL_SKILLS}


def _alias_regex(alias: str):
    if alias.startswith("re:"):
        return re.compile(alias[3:], re.I)
    if alias.startswith("cs:"):
        return re.compile(alias[3:])
    parts = [re.escape(p) for p in re.split(r"\s+", alias.strip())]
    body = r"[\s\-_]*".join(parts)
    # Left: not preceded by a word char. Right: not followed by a word char (".js" style suffixes excluded).
    return re.compile(r"(?<![A-Za-z0-9+#])" + body + r"(?![A-Za-z0-9+#]|\.[A-Za-z])", re.I)


@lru_cache(maxsize=1)
def _compiled():
    out = []
    for canon in ALL_SKILLS:
        aliases = TAXONOMY[SKILL_CATEGORY[canon]][canon]
        seen = set()
        for alias in aliases + [canon]:
            key = alias.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((canon, key, _alias_regex(alias), _probe(alias)))
    return out


def _probe(alias):
    """Cheap substring that must be present for the alias regex to possibly match."""
    if alias.startswith(("re:", "cs:")):
        return None
    return re.split(r"[\s\-_]+", alias.strip().lower())[0] or None


@lru_cache(maxsize=1)
def _alias_index():
    idx = {}
    for canon, alias, _, _ in _compiled():
        if not alias.startswith(("re:", "cs:")):
            idx.setdefault(alias, canon)
    return idx


@lru_cache(maxsize=4096)
def _custom_regex(skill: str):
    return _alias_regex(skill)


def canonicalize(skill: str) -> str:
    """Map a free-form skill string to its canonical taxonomy name when one exists."""
    s = (skill or "").strip()
    if not s:
        return s
    low = s.lower()
    if low in _CANON_LOWER:
        return _CANON_LOWER[low]
    return _alias_index().get(low, s)


def extract_skills(text: str, extra_skills=(), strict=True) -> set:
    """Canonical skills mentioned in free text.

    strict skips generic aliases (see FREE_TEXT_BLOCK).
    extra_skills are user-defined skills that are not in the taxonomy.
    """
    if not text:
        return set()
    found = set()
    low = text.lower()
    for canon, alias, rx, probe in _compiled():
        if canon in found or (strict and alias in FREE_TEXT_BLOCK):
            continue
        if probe and probe not in low:
            continue
        if rx.search(text):
            found.add(canon)
    for sk in extra_skills or ():
        if sk and sk not in found and sk not in SKILL_CATEGORY and _custom_regex(sk).search(text):
            found.add(sk)
    return found


def skills_from_tags(tags, extra_skills=()) -> set:
    """Explicit tag lists from job boards. Generic aliases are accepted here."""
    out = set()
    for t in tags or ():
        if not isinstance(t, str):
            continue
        for piece in re.split(r"[,|;]", t):
            piece = piece.strip()
            if not piece:
                continue
            c = canonicalize(piece)
            if c in SKILL_CATEGORY:
                out.add(c)
            else:
                out |= extract_skills(piece, extra_skills, strict=False)
    return out


def suggest_roles(skills, limit=6):
    have = set(skills)
    scored = []
    for role, req in ROLE_HINTS.items():
        n = len(have & set(req))
        if n >= 2 or (n == 1 and len(req) == 1):
            scored.append((n / len(req) + n * 0.15, role))
    scored.sort(reverse=True)
    return [r for _, r in scored[:limit]]
