# tracker - CMSC 360, Fall 2023, rendezvous codebase

## Installation

```
git clone https://github.com/jbshep/softeng23-manticore
cd softeng23-manticore
python3 -m venv env
source project.env
pip install -r requirements.txt
```

## Build and Test

``` 
source project.env   # if not already in a virtual environment
make
```

`make` runs typechecking and linting checks, then builds an executable, and finally runs unit tests.  Consult the `Makefile` for individual targets.

When determing test coverage, developers may want to do the following:

```
coverage run -m pytests
coverage report -m
```

## Run Command Line Program

``` 
source project.env   # if not already in a virtual environment
tracker              # provides help message on various subcommands
```

## Run Server

``` 
source project.env   # if not already in a virtual environment
run-server
``` 

## Using tracker
tracker is a useful command line tool to help keep track of your projects. There are two different types of projects, local and remote. 
A local project is hosted completely on your device, while a remote project is handled through a server where other people will eventually be able
to access shared projects. In tracker, there are different subcommands the user may call: `delete` `help` `init` `projects` `start` `stop` `summary` 
`switch` `tasks` `show` `connect` `backup` `restore`.

### delete
`delete` will get rid of a currently existing project.

### help
`help` will show the user a list of the different subcommands.

### init
`init` will create a new project. If you want to create a new local project use the command `tracker init [project]`. Otherwise  
`tracker init --remote=[url] --user=[username] [project]` will create a remote project. Local project tasks can be found in the `.tracker` directory and 
remote project tasks will be stored in the tracker project directory under the `.tracker-server` subdirectory and will store a text file under `.tracker` 
containing the name of the project, the project key, and the username given when created. `init` will also reset a project if it has already been created 
and used, it will ask the user first if they wish to overwrite their data.

### projects
`projects` will show the current list of projects and the project that you are currently in will have `*` by its name. Also, if a project is remote, it will be preceded by (remote) all of which will be aligned in a column.

### start
`start` will begin keeping track of a task in the current project that the user is in. If an improper character or already started task is given as the task 
name the user will be told that is an error.

### stop
`stop` will end the timing of a currently started task and store the amount of time that it has been running. If the user stops a task that is not currently 
running or gives an improper character the user will be told that is an error.

#### summary
`summary` will give a report of the amount of time that has been spent on each task in a given project, formatted HH:MM:SS. It will tell the user how long has been spent on
each project as well as what percentage of time has been spent on that project.

### details
`details` will give a report similar to `summary`, that is tell the user how long they have done each task as well as the percentage that task has taken up. 
It will also report which users have worked on each task and how long each of them has done the task.

### switch
`switch` will change the user to a different project specified by the user.

### tasks
`tasks` will show the user the currently tracked tasks in the project. It will tell the user the active tasks and the completed tasks. If a task is in both
that means that the task has previously been stopped by has since been started again.

### show
`show` is dependent on whether the user's current project is local or remote. If local, `show` will tell the user the name of the current project. If 
remote, the user will be given the name of the current project, but they will also be told the project key and the name of the user given when the project
was created.

### connect
`connect` will allow a user to connect to a remote project that has been created by another user. This can be done by calling 
`tracker connect --remote=[host] --user=[username] --key=[key]`, once connected, you should be able to start and stop tasks just as any other project.

### backup
`backup` saves a file acting as a time machine inside a zip file. The zip file will be named `tracker-YYYYMMDDHHmm.zip` YYYY being the current year, MM month, DD day, HH hour, and mm minute. The contents 
inside the file will be the current projects that are on your local device. For local projects, it will get all of the tracker data including the active and finished tasks. Remote projects will only save 
the `remote` text file containing the project data.

### restore
`restore` will take the most recent backup file and overwrite your current data on your local machine to become the data in the backed-up file that you are restoring.
