# CONTRIBUTE

## Introduction
We encourage everyone to help us improve Omnia by contributing to the project. Contributions can be as small as documentation updates or adding example use cases, to adding commenting or properly styling code segments, to full feature contributions. We ask that contributors follow our established guidelines for contributing to the project.

These guidelines are based on the [pravega project](https://github.com/pravega/pravega/).

This document will evolve as the project matures. Please be sure to regularly refer back in order to stay in-line with contribution guidelines.

## How to Contribute to Omnia
Contributions to Omnia are made through [Pull Requests (PRs)](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests). To make a pull request against Omnia, use the following steps:

1. **Create an issue:** [Create an issue](https://help.github.com/en/github/managing-your-work-on-github/creating-an-issue) and describe what you are trying to solve. It does not matter whether it is a new feature, a bug fix, or an improvement. All pull requests need to be associated to an issue.
2. **Create a personal fork:** All work on Omnia should be done in a [fork of the repository](https://help.github.com/en/github/getting-started-with-github/fork-a-repo). Only the maintiners are allowed to commit directly to the project repository.
3. **Issue branch:** [Create a new branch](https://help.github.com/en/desktop/contributing-to-projects/creating-a-branch-for-your-work) on your fork of the repository. All contributions should be branched from `devel`. Use `git checkout devel; git checkout -b <new-branch-name>` to create the new branch.
   * **Branch name:** The branch name should be based on the issue you are addressing. Use the following pattern to create your new branch name: issue-number, e.g., issue-1023.
4. **Commit changes to the issue branch: ** It is important to commit your changes to the issue branch. Commit messages should be descriptive of the changes being made.
5. **Push the changes to your personal repo:** To be able to create a pull request, push the changes to origin: `git push origin <new-branch-name>`. Here I assume that `origin` is your personal repo, e.g., `lwilson/omnia.git`.
6. **Create a pull request:** [Create a pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request) with a title following this format Issue ###: Description (_i.e., Issue 1023: Reformat testutils_). It is important that you do a good job with the description to make the job of the code reviewer easier. A good description not only reduces review time, but also reduces the probability of a misunderstanding with the pull request.

   When preparing a pull request it is important to stay up-to-date with the project repository. We recommend that you rebase against the upstream repo _frequently_. To do this, use the following commands:
   ```
   git pull --rebase upstream master #upstream is dellhpc/omnia
   git push --force origin <pr-branch-name> #origin is your fork of the repository (e.g., <github_user_name>/omnia.git)
   ```
### Omnia Branches and Contribution Flow
The diagram below describes the contribution flow. Omnia has two lifetime branches: `devel` and `master`. The `master` branch is reserved for releases and their associated tags. The `devel` branch is where all development work occurs. The `devel` branch is also the default branch for the project.

![Omnia Branch Flowchart](docs/images/omnia-branch-structure.png "Flowchart of Omnia branches")


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
