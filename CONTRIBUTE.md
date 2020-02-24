# CONTRIBUTE

## Introduction
We encourage everyone to help us improve Omnia by contributing to the project. Contributions can be as small as documentation updates or adding example use cases, to adding commenting or properly styling code segments, to full feature contributions. We ask that contributors follow our established guidelines for contributing to the project.

These guidelines are based on the [pravega project](https://github.com/pravega/pravega/).

This document will evolve as the project matures. Please be sure to regularly refer back in order to stay in-line with contribution guidelines.

## Issues and Pull Requests
To produce a pull request against Omnia, follow these steps:

* **Create an issue:** Create an issue and describe what you are trying to solve. It doesn't matter whether it is a new feature, a bug fix, or an improvement. All pull requests need to be associated to an issue. See more here: Creating an issue
* **Issue branch:** Create a new branch on your fork of the repository. Typically, you need to branch off master, but there could be exceptions. To branch off master, use git checkout master; git checkout -b <new-branch-name>.
* **Push the changes:** To be able to create a pull request, push the changes to origin: git push --set-upstream origin <new-branch-name>. I'm assuming that origin is your personal repo, e.g., `lwilson/omnia.git`.
* **Branch name:** Use the following pattern to create your new branch name: issue-number-description, e.g., issue-1023-reformat-testutils.
* **Create a pull request:** Github gives you the option of creating a pull request. Give it a title following this format Issue ###: Description, _e.g., Issue 1023: Reformat testutils. Follow the guidelines in the description and try to provide as much information as possible to help the reviewer understand what is being addressed. It is important that you try to do a good job with the description to make the job of the code reviewer easier. A good description not only reduces review time, but also reduces the probability of a misunderstanding with the pull request.
* **Merging:** Merging of pull requests will be handled by project mantainers

When preparing a pull request it is important to stay up-to-date with the master. We recommend that you rebase against the upstream repository _frequently_. To do this, use the following commands:
```
git pull --rebase upstream master #upstream is dellhpc/omnia
git push --force origin <pr-branch-name> #origin is your fork of the repository (e.g., <github_user_name>/omnia.git)
```
## Creating an Issue
When creating an issue, there are two important parts: title and description. The title should be succinct, but give a good idea of what the issue is about. Try to add all important keywords to make it clear to the reader. For example, if the issue is about changing the log level of some messages in the segment store, then instead of saying "Log level" say "Change log level in the segment store". The suggested way includes both the goal where in the code we are supposed to do it.

For the description, there three parts:

* *Problem description:* Describe what it is that we need to change. If it is a bug, describe the observed symptoms. If it is a new feature, describe it is supposed to be with as much detail as possible.

* *Problem location:* This part refers to where in the code we are supposed to make changes. For example, if it is bug in the client, then in this part say at least "Client". If you know more about it, then please add it. For example, if you that there is an issue with SegmentOutputStreamImpl, say it in this part.

* *Suggestion for an improvement:* This section is designed to let you give a suggestion for how to fix the bug described in the Problem description or how to implement the feature described in that same section. Please make an effort to separate between problem statement (Problem Description section) and solution (Suggestion for an improvement).

We next discuss how to create a pull request.

## Creating a Pull Request
When creating a pull request, there are also two important parts: title and description. The title can be the same as the one of the issue, but it must be prefixed with the issue number, e.g.:
```
Issue 724: Change log level in the segment store
```
The description has four parts:

* __Changelog description*:__ This section should be the two or three main points about this PR. A detailed description should be left for the What the code does section. The two or three points here should be used by a committer for the merge log.
* __Purpose of the change:__ Say whether this closes an issue or perhaps is a subtask of an issue. This section should link the PR to at least one issue.
* __What the code does:__ Use this section to freely describe the changes in this PR. Make sure to give as much detail as possible to help a reviewer to do a better job understanding your changes.
* __How to verify it:__ For most of the PRs, the answer here will be trivial: the build must pass, system tests must pass, visual inspection, etc. This section becomes more important when the way to reproduce the issue the PR is resolving is non-trivial, like running some specific command or workload generator.

## Signing Your Commits
We require that developers sign off their commits to certify that they have permission to contribute the code in a pull request. This way of certifying is commonly known as the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). We encourage all contributors to read the DCO text before signing a commit and making contributions.

To make sure that pull requests have all commits signed off, we use the [Probot DCO plugin](https://probot.github.io/apps/dco/).

### Signing off a commit

#### Using the command line
To make sure that pull requests have all commits signed off, we use the Probot DCO plugin.
Use either `--signoff` or `-s` with the commit command.

Make sure you have your user name and e-mail set. The `--signoff | -s` option will use the configured user name and e-mail, so it is important to configure it before the first time you commit. Check the following references:

[Setting up your github user name](https://help.github.com/articles/setting-your-username-in-git/)

[Setting up your e-mail address](https://help.github.com/articles/setting-your-commit-email-address-in-git/)
