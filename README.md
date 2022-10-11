<img src="docs/source/images/omnia-logo.png" width="500px">
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
<!-- DO NOT ADD A BADGE -->
<!-- ALL-CONTRIBUTORS-BADGE:END -->


![GitHub](https://img.shields.io/github/license/dellhpc/omnia) ![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/dellhpc/omnia?include_prereleases) ![GitHub last commit (branch)](https://img.shields.io/github/last-commit/dellhpc/omnia/devel) ![GitHub commits since tagged version](https://img.shields.io/github/commits-since/dellhpc/omnia/v1.3.1/devel)

![All contributors](https://img.shields.io/github/all-contributors/dellhpc/omnia) ![GitHub forks](https://img.shields.io/github/forks/dellhpc/omnia) ![GitHub Repo stars](https://img.shields.io/github/stars/dellhpc/omnia) ![GitHub all releases](https://img.shields.io/github/downloads/dellhpc/omnia/total)

![GitHub issues](https://img.shields.io/github/issues-raw/dellhpc/omnia) ![GitHub Discussions](https://img.shields.io/github/discussions/dellhpc/omnia)[<img src="https://img.shields.io/badge/slack-dellhpc-blue.svg?logo=slack">](https://app.slack.com/client/TH80K68HY/C018L5109PW)

#### Ansible playbook-based deployment of Slurm and Kubernetes on servers running an RPM-based Linux OS

Omnia (Latin: all or everything) is a deployment tool to turn servers with RPM-based Linux images into functioning Slurm/Kubernetes clusters.

## Pre Requisites before installing Omnia
- [Python3](https://www.python.org/)
- [Ansible  2.12.9](https://www.ansible.com/)
- [RockyOS](https://rockylinux.org/) / [Red Hat](https://www.redhat.com/en/enterprise-linux-8)


# Using Omnia

1. Run the [pre-req script](https://omnia-documentation.readthedocs.io/en/latest/InstallationGuides/RunningInit/index.html) to ready your system for Omnia. 
2. Run the [provision tool](https://omnia-documentation.readthedocs.io/en/latest/InstallationGuides/InstallingProvisionTool/index.html) to deploy servers with the OS required.
3. Run the [monitoring tool](https://omnia-documentation.readthedocs.io/en/latest/Roles/Monitor/index.html) to set up Grafana and Prometheus.


## Troubleshooting Omnia
* For a list of commonly encountered issues, check out our [FAQs](https://omnia-documentation.readthedocs.io/en/latest/Troubleshooting/FAQ.html).
* To troubleshoot Omnia, use our [Troubleshooting Guide](https://omnia-documentation.readthedocs.io/en/latest/Troubleshooting/troubleshootingguide.html).

## Omnia Documentation
For Omnia documentation, please see the [website](https://omnia-documentation.readthedocs.io/en/latest/index.html).

## Omnia Community Members:
<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Dell_Technologies_logo.svg/512px-Dell_Technologies_logo.svg.png" height="50px" alt="Dell Technologies">
<img src="https://upload.wikimedia.org/wikipedia/commons/0/0e/Intel_logo_%282020%2C_light_blue%29.svg" height="50px" alt="Intel Corporation">

<img src="docs/source/images/pisa.png" height="100px" alt="Universita di Pisa"> <img src="https://user-images.githubusercontent.com/83095575/117071024-64956c80-ace3-11eb-9d90-2dac7daef11c.png" height="80px" alt="Arizona State University"> 
<img src="https://user-images.githubusercontent.com/5414112/153955170-0a4b199a-54f0-42af-939c-03eac76881c0.png" height="100px" alt="Texas Tech University">

<img src="https://www.eweek.com/wp-content/uploads/2020/10/Liquid-1.jpg" height="50px" alt="LIQID Inc.">

## Contributors
Our thanks go to everyone who makes Omnia possible ([emoji key](https://allcontributors.org/docs/en/emoji-key)):
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="http://johnlockman.com"><img src="https://avatars.githubusercontent.com/u/912987?v=4?s=100" width="100px;" alt=""/><br /><sub><b>John Lockman</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=j0hnL" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=j0hnL" title="Code">💻</a> <a href="#blog-j0hnL" title="Blogposts">📝</a> <a href="#ideas-j0hnL" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-j0hnL" title="Maintenance">🚧</a> <a href="#mentoring-j0hnL" title="Mentoring">🧑‍🏫</a> <a href="#design-j0hnL" title="Design">🎨</a> <a href="https://github.com/dellhpc/omnia/pulls?q=is%3Apr+reviewed-by%3Aj0hnL" title="Reviewed Pull Requests">👀</a> <a href="#talk-j0hnL" title="Talks">📢</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Aj0hnL" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/lwilson"><img src="https://avatars.githubusercontent.com/u/1236922?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lucas A. Wilson</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=lwilson" title="Code">💻</a> <a href="#design-lwilson" title="Design">🎨</a> <a href="#maintenance-lwilson" title="Maintenance">🚧</a> <a href="#ideas-lwilson" title="Ideas, Planning, & Feedback">🤔</a> <a href="#blog-lwilson" title="Blogposts">📝</a> <a href="https://github.com/dellhpc/omnia/commits?author=lwilson" title="Documentation">📖</a> <a href="#mentoring-lwilson" title="Mentoring">🧑‍🏫</a> <a href="#projectManagement-lwilson" title="Project Management">📆</a> <a href="https://github.com/dellhpc/omnia/pulls?q=is%3Apr+reviewed-by%3Alwilson" title="Reviewed Pull Requests">👀</a> <a href="#talk-lwilson" title="Talks">📢</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Alwilson" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/sujit-jadhav"><img src="https://avatars.githubusercontent.com/u/73123831?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Sujit Jadhav</b></sub></a><br /><a href="#ideas-sujit-jadhav" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/dellhpc/omnia/commits?author=sujit-jadhav" title="Documentation">📖</a> <a href="https://github.com/dellhpc/omnia/commits?author=sujit-jadhav" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/pulls?q=is%3Apr+reviewed-by%3Asujit-jadhav" title="Reviewed Pull Requests">👀</a> <a href="#maintenance-sujit-jadhav" title="Maintenance">🚧</a> <a href="#projectManagement-sujit-jadhav" title="Project Management">📆</a> <a href="#mentoring-sujit-jadhav" title="Mentoring">🧑‍🏫</a> <a href="#talk-sujit-jadhav" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/DeepikaKrishnaiah"><img src="https://avatars.githubusercontent.com/u/73213880?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Deepika K</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=DeepikaKrishnaiah" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=DeepikaKrishnaiah" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3ADeepikaKrishnaiah" title="Bug reports">🐛</a> <a href="#security-DeepikaKrishnaiah" title="Security">🛡️</a> <a href="#talk-DeepikaKrishnaiah" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/sakshiarora13"><img src="https://avatars.githubusercontent.com/u/73195862?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Sakshi Arora</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=sakshiarora13" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Asakshiarora13" title="Bug reports">🐛</a> <a href="#talk-sakshiarora13" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/abhishek-sa1"><img src="https://avatars.githubusercontent.com/u/94038029?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Abhishek SA</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=abhishek-sa1" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Aabhishek-sa1" title="Bug reports">🐛</a> <a href="https://github.com/dellhpc/omnia/commits?author=abhishek-sa1" title="Documentation">📖</a> <a href="https://github.com/dellhpc/omnia/commits?author=abhishek-sa1" title="Tests">⚠️</a> <a href="#maintenance-abhishek-sa1" title="Maintenance">🚧</a> <a href="#talk-abhishek-sa1" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/Shubhangi-dell"><img src="https://avatars.githubusercontent.com/u/72869337?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Shubhangi Srivastava</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Shubhangi-dell" title="Code">💻</a> <a href="#maintenance-Shubhangi-dell" title="Maintenance">🚧</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3AShubhangi-dell" title="Bug reports">🐛</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/cgoveas"><img src="https://avatars.githubusercontent.com/u/88071888?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Cassey Goveas</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=cgoveas" title="Documentation">📖</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Acgoveas" title="Bug reports">🐛</a> <a href="#maintenance-cgoveas" title="Maintenance">🚧</a> <a href="#talk-cgoveas" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/Khushboodholi"><img src="https://avatars.githubusercontent.com/u/12014935?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Khushboo Dholi</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Khushboodholi" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/araji"><img src="https://avatars.githubusercontent.com/u/216020?v=4?s=100" width="100px;" alt=""/><br /><sub><b>araji</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=araji" title="Code">💻</a></td>
    <td align="center"><a href="https://mike.renf.ro/blog/"><img src="https://avatars.githubusercontent.com/u/1451881?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Mike Renfro</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=mikerenfro" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/leereyno-asu"><img src="https://avatars.githubusercontent.com/u/81774548?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lee Reynolds</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=leereyno-asu" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=leereyno-asu" title="Documentation">📖</a> <a href="#tutorial-leereyno-asu" title="Tutorials">✅</a></td>
    <td align="center"><a href="https://github.com/blesson-james"><img src="https://avatars.githubusercontent.com/u/72782936?v=4?s=100" width="100px;" alt=""/><br /><sub><b>blesson-james</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=blesson-james" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=blesson-james" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/issues?q=author%3Ablesson-james" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/avinashvishwanath"><img src="https://avatars.githubusercontent.com/u/77823538?v=4?s=100" width="100px;" alt=""/><br /><sub><b>avinashvishwanath</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=avinashvishwanath" title="Documentation">📖</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/abhishek-s-a"><img src="https://avatars.githubusercontent.com/u/73212230?v=4?s=100" width="100px;" alt=""/><br /><sub><b>abhishek-s-a</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=abhishek-s-a" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=abhishek-s-a" title="Documentation">📖</a> <a href="https://github.com/dellhpc/omnia/commits?author=abhishek-s-a" title="Tests">⚠️</a></td>
    <td align="center"><a href="https://github.com/Franklin-Johnson"><img src="https://avatars.githubusercontent.com/u/84760103?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Franklin-Johnson</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Franklin-Johnson" title="Code">💻</a> <a href="#blog-Franklin-Johnson" title="Blogposts">📝</a></td>
    <td align="center"><a href="https://github.com/teiland7"><img src="https://avatars.githubusercontent.com/u/85184708?v=4?s=100" width="100px;" alt=""/><br /><sub><b>teiland7</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=teiland7" title="Code">💻</a> <a href="#blog-teiland7" title="Blogposts">📝</a></td>
    <td align="center"><a href="https://github.com/VishnupriyaKrish"><img src="https://avatars.githubusercontent.com/u/72784834?v=4?s=100" width="100px;" alt=""/><br /><sub><b>VishnupriyaKrish</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=VishnupriyaKrish" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=VishnupriyaKrish" title="Tests">⚠️</a></td>
    <td align="center"><a href="https://rb.gy/ndlbhv"><img src="https://avatars.githubusercontent.com/u/48859631?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Ishita Datta</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=ishitadatta" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/asu-wdizon"><img src="https://avatars.githubusercontent.com/u/81772355?v=4?s=100" width="100px;" alt=""/><br /><sub><b>William Dizon</b></sub></a><br /><a href="#tutorial-asu-wdizon" title="Tutorials">✅</a></td>
    <td align="center"><a href="https://github.com/bssitton-BU"><img src="https://avatars.githubusercontent.com/u/14130464?v=4?s=100" width="100px;" alt=""/><br /><sub><b>bssitton-BU</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Abssitton-BU" title="Bug reports">🐛</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/hearnsj"><img src="https://avatars.githubusercontent.com/u/19259589?v=4?s=100" width="100px;" alt=""/><br /><sub><b>John Hearns</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Ahearnsj" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/renzo-granados"><img src="https://avatars.githubusercontent.com/u/83035817?v=4?s=100" width="100px;" alt=""/><br /><sub><b>renzo-granados</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Arenzo-granados" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/kbuggenhout"><img src="https://avatars.githubusercontent.com/u/30471699?v=4?s=100" width="100px;" alt=""/><br /><sub><b>kris buggenhout</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Akbuggenhout" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/jiad-vmware"><img src="https://avatars.githubusercontent.com/u/68653329?v=4?s=100" width="100px;" alt=""/><br /><sub><b>jiad-vmware</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Ajiad-vmware" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://jlec.de"><img src="https://avatars.githubusercontent.com/u/79732?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Justin Lecher</b></sub></a><br /><a href="#ideas-jlec" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/Kavyabr23"><img src="https://avatars.githubusercontent.com/u/90390587?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Kavyabr23</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Kavyabr23" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=Kavyabr23" title="Tests">⚠️</a></td>
    <td align="center"><a href="https://github.com/vedaprakashanp"><img src="https://avatars.githubusercontent.com/u/90596073?v=4?s=100" width="100px;" alt=""/><br /><sub><b>vedaprakashanp</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=vedaprakashanp" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=vedaprakashanp" title="Code">💻</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/Bhagyashree-shetty"><img src="https://avatars.githubusercontent.com/u/90620926?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Bhagyashree-shetty</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Bhagyashree-shetty" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=Bhagyashree-shetty" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/nihalranjan-hpc"><img src="https://avatars.githubusercontent.com/u/84398828?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Nihal Ranjan</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=nihalranjan-hpc" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=nihalranjan-hpc" title="Code">💻</a> <a href="#talk-nihalranjan-hpc" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/ptrinesh"><img src="https://avatars.githubusercontent.com/u/73214211?v=4?s=100" width="100px;" alt=""/><br /><sub><b>ptrinesh</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=ptrinesh" title="Code">💻</a></td>
    <td align="center"><a href="https://bandism.net/"><img src="https://avatars.githubusercontent.com/u/22633385?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Ikko Ashimine</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=eltociear" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/Lakshmi-Patneedi"><img src="https://avatars.githubusercontent.com/u/94051091?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lakshmi-Patneedi</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Lakshmi-Patneedi" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/Artlands"><img src="https://avatars.githubusercontent.com/u/31781106?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Jie Li</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Artlands" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/githubyongchen"><img src="https://avatars.githubusercontent.com/u/5414112?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Yong Chen</b></sub></a><br /><a href="#design-githubyongchen" title="Design">🎨</a></td>
  </tr>
  <tr>
    <td align="center"><a href="http://www.myweb.ttu.edu/ngu00336/"><img src="https://avatars.githubusercontent.com/u/18387748?v=4?s=100" width="100px;" alt=""/><br /><sub><b>nvtngan</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Zipexpo" title="Code">💻</a> <a href="#plugin-Zipexpo" title="Plugin/utility libraries">🔌</a></td>
    <td align="center"><a href="https://github.com/tamilarasansubrama1"><img src="https://avatars.githubusercontent.com/u/100588942?v=4?s=100" width="100px;" alt=""/><br /><sub><b>tamilarasansubrama1</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=tamilarasansubrama1" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=tamilarasansubrama1" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/shemasr"><img src="https://avatars.githubusercontent.com/u/100141664?v=4?s=100" width="100px;" alt=""/><br /><sub><b>shemasr</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Ashemasr" title="Bug reports">🐛</a> <a href="https://github.com/dellhpc/omnia/commits?author=shemasr" title="Code">💻</a> <a href="https://github.com/dellhpc/omnia/commits?author=shemasr" title="Tests">⚠️</a></td>
    <td align="center"><a href="https://github.com/naresh3774"><img src="https://avatars.githubusercontent.com/u/101410892?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Naresh Sharma</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Anaresh3774" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/JonHass"><img src="https://avatars.githubusercontent.com/u/6976486?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Jon Hass</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=JonHass" title="Documentation">📖</a> <a href="#design-JonHass" title="Design">🎨</a></td>
    <td align="center"><a href="https://github.com/KalyanKonatham"><img src="https://avatars.githubusercontent.com/u/101596828?v=4?s=100" width="100px;" alt=""/><br /><sub><b>KalyanKonatham</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3AKalyanKonatham" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/rahulakolkar"><img src="https://avatars.githubusercontent.com/u/22768133?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Rahul Akolkar</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/issues?q=author%3Arahulakolkar" title="Bug reports">🐛</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/srinandini-karumuri"><img src="https://avatars.githubusercontent.com/u/104345504?v=4?s=100" width="100px;" alt=""/><br /><sub><b>srinandini-karumuri</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=srinandini-karumuri" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/Rishabhm47"><img src="https://avatars.githubusercontent.com/u/106973551?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Rishabhm47</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=Rishabhm47" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=Rishabhm47" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/vaishakh-pm"><img src="https://avatars.githubusercontent.com/u/104622022?v=4?s=100" width="100px;" alt=""/><br /><sub><b>vaishakh-pm</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=vaishakh-pm" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=vaishakh-pm" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/shridhar-sharma"><img src="https://avatars.githubusercontent.com/u/104621992?v=4?s=100" width="100px;" alt=""/><br /><sub><b>shridhar-sharma</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=shridhar-sharma" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=shridhar-sharma" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/JayaDayyala"><img src="https://avatars.githubusercontent.com/u/108455487?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Jaya.Dayyala</b></sub></a><br /><a href="https://github.com/dellhpc/omnia/commits?author=JayaDayyala" title="Tests">⚠️</a> <a href="https://github.com/dellhpc/omnia/commits?author=JayaDayyala" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->