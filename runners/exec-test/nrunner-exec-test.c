/*
 * Avocado "N(ext) Runner" compatible runner for exec and exec-test runnables
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>


// The amount of time (in seconds) between each internal status check
#define RUNNER_RUN_CHECK_INTERVAL 0.01

// The amount of time (in seconds) between a status report from a
// runner that performs its work asynchronously
#define RUNNER_RUN_STATUS_INTERVAL 0.5


static const char *capabilities[] = {
    "noop",
    "exec",
    "exec-test",
    NULL
};


#define CMD_RUNNABLES_CAPABLE "runnables-capable"
#define CMD_RUNNABLE_RUN "runnable-run"


void print_runnable_capables(void) {
  for (int i = 0; i <= sizeof(capabilities); i++) {
    if (capabilities[i] == NULL) {
      break;
    }
    printf(capabilities[i]);
    printf("\n");
  }
}

void usage(int status) {
  printf("usage: nrunner [command] [opts]\n");
  exit(status);
}

static const struct option long_options[] = {
  {"kind", required_argument, NULL, 'k'},
  {"uri", required_argument, NULL, 'u'},
  {"help", no_argument, NULL, 'h'},
  {NULL, 0, NULL, 0}
};

int runnable_run(const char *kind, const char *uri) {
  printf("Running runnable:\n");
  printf(" kind => %s\n", kind);
  printf(" uri => %s\n", uri);

  return 0;
}

static void parse(int argc, char *argv[], const char **command, const char **kind, const char **uri) {
  int optc;
  int lose = 0;
  while ((optc = getopt_long (argc, argv, "k:u:", long_options, NULL)) != -1)
    switch (optc)
      {
      case 'h':
        usage(0);
      case 'k':
	*kind = optarg;
	break;
      case 'u':
        *uri = optarg;
      default:
	lose = 1;
	break;
      }

  if ((lose || optind < argc) && (argv[optind]))
    *command = argv[optind];
}


int main (int argc, char *argv[]) {

  const char *command = NULL;
  const char *kind = NULL;
  const char *uri = NULL;

  parse(argc, argv, &command, &kind, &uri);
  if (!command)
    usage(1);

  if (!strncmp(command, CMD_RUNNABLE_RUN, sizeof(CMD_RUNNABLE_RUN))) {
    exit(runnable_run(kind, uri));
  } else if (!strcmp(command, CMD_RUNNABLES_CAPABLE)) {
    print_runnable_capables();
  }
  return 0;
}
