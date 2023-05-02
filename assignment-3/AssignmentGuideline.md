# Assignment guidelines

Last modified: 12.12.2020
>Note: this guideline can be stayed in your submission. This guideline should not be modified by you.

The assignment delivery will be everything within the top directory **assignment_nr_studentid**. You **MUST use git** to work on your assignment delivery by cloning this assignment delivery template (it is up to you to decide which git systems you want to use).
* if you are not familar with GIT: try to read [GIT cheatsheet](https://www.atlassian.com/git/tutorials/atlassian-git-cheatsheet) and use common services like [Aalto GIT](https://version.aalto.fi), [GitHub](https://github.com), [GitLab](https://gitlab.com), and [Bitbucket](https://bitbucket.org/)

## Important files

* Your student id should be in the **submitter.csv**.
* The assignment id and your student id should be in the name of the top directory of the assignment delivery
* Self-evaluation: do the self-evaluation of your assignment and put the points of your self-evaluation into **selfgrading.csv**
* **assignment-git.log**: the content of this file is the log extracted from your own git project for the assignment. You can use "git log" command to extract the git log

## Directory structure

* You must make sure that the top directory is named as "assignment_nr_studentid" by replacing "nr" with the assignment number and "studentid" with your student id.
* We have subdirectory:
   - *data*: for describing data. Do not put large dataset into this directory. You can put a small sample of data and/or indicate a public place where the data can be downloaded.
   - *code*: where you can put source code written by you (or source code modified by you)
   - *logs*: where you put logs generated from test programs or service logs that can be used to back up your report
   - *report*: where you put for reports about design, performance, etc.

## Content in the assignment

* No sensitive information should be stored in the assignment delivery (data, source, logs, reports)
* You must guarantee the data regulation w.r.t. all contents in the assignment delivery
* Only your student id should be stored in the delivery: the **submitter.csv** should have only a single line which is your student id.
* Reports have to be written in [Markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
* No **BINARY format** for any content (code, data, logs, reports), except *figures of your design or performance charts*. It means, for example, external libraries for your programs should be automatically downloaded when we compile the code (following your README guide), no report is written in Microsoft/Open office or PDF.
* If you make a video demonstrating how your systems/tests work, you can put the video into any accessible link (e.g., private Youtube) and put the link into *demolink.txt*

## Programming Languages
You must use only **Java, JavaScript/TypeScript, Python, or shell scripts**
>If you want to use other programming languages you can discuss with the responsible teacher

## Recommendations:
To increase the clarity of the source code, the platform needs to be well structured. The components should be organized into separate folders providing a manuscript to run.

## Assignment submission

* Make sure your clean your directory before creating a zip file for submission.
* The zip file should **assignment-nr-studentid.zip** which, when unzipped, will be **assignment-nr-studentid** directory.
* The zip file will be submitted into [Mycourses](http://mycourses.aalto.fi)
* All deadlines are hard so make sure you test the submission in advance.
