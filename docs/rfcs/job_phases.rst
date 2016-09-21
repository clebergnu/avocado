===================
 RFC on Job phases
===================

This is a simple proposal for the execution phases/steps of the
Avocado Job class.  Based on its natural organic evolution, some of
the job steps purposes do not have a clearly defined responsibility.

The original motivation of this RFC is to discuss and fix issue
reported on GitHub PR #1412.  On that issue/PR, it was noticed that
result plugins would be run after the `--archive|-z` feature, thus
missing some of the results.  To add to the confusion, the user's own
Post-Job plugin was also executed in an order that was not intended.

Clear job phases, and also order control on plugin execution (not the
scope of this RFC) are being proposed as two abstract mechanisms that
would allow a definitive fix for that (and other similar) issues.

Current Job execution phases
============================

A Job is instantiated at `avocado.plugins.Run.run()`::

  ...
  job_instance = job.Job(args)
  ...

At this point, as part of `avocado.core.job.Job.__init__()`, the
Pre-job dispatcher is instantiated (but not yet executed)::

  ...
  self.job_pre_post_dispatcher = dispatcher.JobPrePostDispatcher()
  output.log_plugin_failures(self.job_pre_post_dispatcher.load_failures)
  ...

When the job instance is *run*, that is, `avocado.core.job.Job.run()`
is called from `avocado.plugins.Run.run()` many other relevant actions
are performed::

  ...
  job_run = job_instance.run()
  ...

`avocado.core.job.Job.run()` calls an "unhandled"
`avocado.core.job.Job._run()` method that executes the Pre-job
dispatcher::

  ...
  self.job_pre_post_dispatcher.map_methods('pre', self)
  ...

Then Post-job dispatcher executed at the end of `avocado.core.job.Job.run()`::

  ...
  finally:
     self.job_pre_post_dispatcher.map_methods('post', self)
  ...

Finally, results are generated at `avocado.plugins.Run.run()`, after
`avocado.core.job.Job.run()`::

  ...
  result_dispatcher = ResultDispatcher()
  if result_dispatcher.extensions:
      # At this point job_instance doesn't have a single results attribute
      # which is the end goal.  For now, we pick any of the plugin classes
      # added to the result proxy.
      if len(job_instance.result_proxy.output_plugins) > 0:
          result = job_instance.result_proxy.output_plugins[0]
          result_dispatcher.map_method('render', result, job_instance)
  ...


Proposal for Job execution phases
=================================

Job instantiation
-----------------

Jobs will continue to be instantiated at `avocado.plugins.Run.run()`::

  ...
  job_instance = job.Job(args)
  ...

In fact, allowing other pieces of code to instantiate and manipulate a
job should is one of the building blocks of the Job API.

Test suite
----------

Right after a Job is created, it has no test suite defined.  A formal
job execution step, to be called "create_test_suite" is going to be defined.

This is where the resolution of test names will be done, and a test suite
will be created as class attribute named `test_suite`.

Using the current code as example, the following block of code, will
probably make up for a big (or all) implementation of
"create_test_suite"::

   if (getattr(self.args, 'remote_hostname', False) and
      getattr(self.args, 'remote_no_copy', False)):
       self.test_suite = [(None, {})]
   else:
       try:
           self.test_suite = self._make_test_suite(self.urls)
       except loader.LoaderError as details:
           stacktrace.log_exc_info(sys.exc_info(), 'avocado.app.debug')
           self._remove_job_results()
           raise exceptions.OptionValidationError(details)

Please note that some changes will certainly be necessary here.
Raising `OptionValidationErrors` at this point, for instance, does not
feel appropriate.

Pre-tests execution
-------------------

A new job execution phase called "pre_tests" will be created.  The
dispatcher instantiation can happen at this time, that is
`avocado.core.job.Job.pre_tests` can look something like::

  ...
  def pre_tests(self):
      self.job_pre_post_dispatcher = dispatcher.JobPrePostDispatcher()
      output.log_plugin_failures(self.job_pre_post_dispatcher.load_failures)
      self.job_pre_post_dispatcher.map_methods('pre', self)
  ...

Pre-job plugins would be renamed, thus better named, "job pre-tests"
(note the plural).

Tests execution
---------------

As mentioned before, the current implementation of the
`avocado.core.Job.run()` method indirectly includes other job steps,
such as creating the test suite.

The execution of tests should be a more clearly defined and properly
named step.  The proposal here is to name the test execution step
"run_tests", which will run *all* tests previously defined in
`Job.test_suite`.

Post-tests execution
--------------------

A new job execution phase called "post_tests" will be created.  The
dispatcher instantiation, if not already performed during the
"pre_tests" phase, will be done here.  This is what
`avocado.core.job.Job.post_tests` can look something like::

  ...
  def post_tests(self):
      if self.job_pre_post_dispatcher is None:
          self.job_pre_post_dispatcher = dispatcher.JobPrePostDispatcher()
          output.log_plugin_failures(self.job_pre_post_dispatcher.load_failures)
      self.job_pre_post_dispatcher.map_methods('post', self)
  ...

Post-job plugins would be renamed, thus better named, "job post-tests"
(note the plural).

Job overall execution
---------------------

The job overall execution is certainly a valid use case.  That is, in
some cases, it may be desirable to create the test suite, run the
pre-tests execution plugins, run the tests and all other steps defined
here at once.

A method called `run()`, meaning the execution of all job phases, can
formally be defined as the execution of all steps of a job.  Its
implementation could look something like::

  def run(self):
      self.create_test_suite()
      # at this point, self.test_suite contains all tests resolved by
      # the various test loaders enabled,  which could in fact be
      # an empty test suite.

      # now run the pre_tests step, which include pre-tests execution
      # plugins
      self.pre_tests()

      # run all tests
      self.run_tests()

      # now run the post_tests step, which include post-tests
      # execution plugins
      self.post_tests()

Job results
-----------

There's been already a lot of work towards moving the generation of
results outside the job.  The proposal here is to maintain the same
approach.

Conclusion
==========

The most important point here is to properly define steps and
responsibilities of each job phase.

For that, each job phase should be self contained, and it should be
possible, to skip one of the defined steps and still have a
functioning job instance.

One quick example is a custom Job instance written like this::

  ...
  job = job.Job(args)
  job.create_test_suite()
  job.run_tests()
  ...

This Job will have no pre/post-tests plugins executed.  Other than that,
it should still perform a fully functional job.
