===========================
 Multi Stream Test Support
===========================

Introduction
============

Avocado currently does not provide test writers with standard tools
or guidelines for developing tests that spawn multiple machines.

Since these days the concept of a "machine" is blurring really
quickly, this proposal for Avocado's version of "multi machine" test
support is more abstract (that's an early and quick explanation of
what a "stream" means).  One of the major goal is to be more flexible
and stand the "test" (pun intended) of time.

This is a counter proposal to a previous RFC posted and discussed on
Avocado development mailing list.  Many of the concepts detailed here
were introduced there:

* https://www.redhat.com/archives/avocado-devel/2016-March/msg00025.html
* https://www.redhat.com/archives/avocado-devel/2016-March/msg00035.html
* https://www.redhat.com/archives/avocado-devel/2016-April/msg00042.html
* https://www.redhat.com/archives/avocado-devel/2016-April/msg00072.html

Background
==========

The prior art that influences Avocado the most is Autotest.  The
reason is that many of the Avocado developers worked on Autotest
before, and both share various common goals.  Let's use Autotest,
which provided support for multiple machine test support as a basis
for comparison.

Back in the Autotest days, a test that would spawn multiple machines
was a very particular type of test.  To write such a test, one would
write a **different** type of "control file" (a server one).  Then, by
running a "server control file" with an **also different** command
line application (``autoserv``, A.K.A. ``autotest-remote``), the
server control file would have access to some special variables, such
as the ``machines`` one.  By using an **also different** type of job
implementation, the control file could run a given **Python function**
on these various ``machines``.

An actual sample server control file (``server/samples/reboot.srv``)
for Autotest looks like this::

   1  def run(machine):
   2     host = hosts.create_host(machine)
   3     host.reboot()
   4
   5  job.parallel_simple(run, machines)

Line #5 makes use of the different (server) job implementation to run
function ``run`` (defined in line #1) in parallel on machines given by
the special variable ``machines`` (made available by the also special
``autoserv`` tool).

This quick background check shows two important facts:

1) The functionality is not scoped to tests.  It's not easy to understand
   where a test begins or ends by looking at such a control file.

2) Users (and most importantly test writers) have to learn about
   different tools and APIs when writing "multi machine" code;

3) The machines are defined outside the test itself (in the form of
   arguments to the ``autoserv`` command line application);

Please keep these Autotest characteristics in mind: Avocado's multi
stream test support goals will be presented shortly, and will detail
how they contrast with those.

Avocado's Multi Stream Test Support Goals
=========================================

This is a hopefully complete summary of our goals:

1) To not require a different type of test, that is, allow users
   to *write* a plain `avocado.Test` while still having access to
   multi stream goodies;

2) To allow for clear separation between the test itself and its
   execution environment (focus here on the execution streams
   environment);

3) To allow increased flexibility by abstracting the "machines"
   concept into "excution streams";

4) To allow for even increased flexibility by allowing test writers to
   use not only Python functions, but other representations of code to
   be executed on those separate streams;

Comparison with prior art
-------------------------

When compared to the Autotest version of multiple machine support for
tests, Avocado's version is similar in that it keeps the separation of
machine and test definition.  That means that tests written in
accordance to the official guidelines, will not contain reference to
the machines ("execution streams") on which they will have portions of
themselves executed on.

But, a major difference from the Autotest version is that this
proposal attempts to provide the **same basic tools and test APIs** to
the test writers needing the multiple stream support.  Of course,
additional tools and APIs will be available, but they will not
incompatible with traditional Avocado INSTRUMENTED tests.

Core concepts
=============

Because the first goal of this RFC is to set the general scope and
approach to Multi Stream test support, it's important to properly
describe each of the core concepts (usually abstractions) that will be
used in later parts of this document.

Execution Stream
----------------

An *Execution Stream* is defined as a disposable execution environment,
different and ideally isolated from the main test execution environment.

A simplistic but still valid implementation of an execution
environment could be based on an Operating System level process.
Another valid implementation would be based on a lightweight
container.  Yet another valid example could be based on a remote
execution interface (such as a secure shell connection).

These examples makes it clear that level of isolation is determined
solely by the implementation.

 .. note:: Even though the idea is very similar, the term *thread* was
           intentionally avoided here, so that readers are not led to think
           that the architecture is based on an OS level thread.

An execution stream is the *"where"* to execute a "Block Of Code"
(which is the *"what"*).

Block of Code
-------------

A *Block of Code* is defined as computer executable code that can run
from start to finish under a given environment and is able to report
its outcome.

For instance, a command such as ``grep -q vmx /proc/cpuinfo; echo $?``
is valid computer executable code that can run under various shell
implementations.  A Python function or module, a shell command, or
even an Avocado INSTRUMENTED test could qualify as a block of code,
given that an environment knows how to run them.

Again, this is the *what* to be run on a "Execution Streams" (which,
in turn, is *"where"* it can be run).

Basic interface
===============

Without initial implementation attempts, it's unreasonable to document
interfaces at this point and do not expect them to change.  Still, the
already existing understanding of use cases suggests an early view of
the interfaces that would be made available.

Execution Stream Interface
--------------------------

One individual execution stream, within the context of a test, should
allow its users (test writers) to control it with a clean interface.
Actions that an execution stream implementation should provide:

* ``run``: Starts the execution of the given block of code (async,
  non-blocking).
* ``wait``: Block until the execution of the block of code has
  finished.  ``run`` can be given a ``wait`` parameter that will
  automatically block until the execution of code has finished.
* ``terminate``: Terminate the execution stream, interrupting the
  execution of the block of code and freeing all resources
  associated with this disposable environment

The following properties should be provided to let users monitor the
progress and outcome of the execution:

* ``active``: Signals with True or False wether the block of code
  given on ``run`` has finished executing.  This will always return
  False if ``wait`` is used, but can return either True or False when
  running in async mode.
* ``success``: A simplistic but precise view of the outcome of the
  execution.
* ``output``: A dictionary of various outputs that may have been
  created by ``run``, keyed by a descriptive name.

The following properties could be provided to transport block of code
payloads to the execution environment:

* ``send``: Sends the given content to the execution stream
  environment.

Block of Code Interface for test writers
----------------------------------------

When a test writer intends to execute a block code, he must choose from
one of the available implementations.  Since the test writer must know
what type of code it's executing, the user inteface with the implementation
can be much more flexible.

For instance, suppose a Block Of Code implementation called
``PythonModule`` exists.  This implementation would possibly run something like
``python -m <modulename>`` and collect its outcome.

A user of such an implementation could write a test such as::

  from avocado import Test
  from avocado.streams.code import PythonModule

  class ModuleTest(Test):
    def test(self):
        self.streams[1].run(PythonModule("mymodule",
                                         path=["/opt/myproject"]))

The ``path`` interface in this example is made available and supported
by the ``PythonModule`` implementation alone and will not be used the
execution stream implementations. As a general rule, the "payload"
should be the first argument to all block of code implementations.
Other arguments can follow.

Another possibility related to parameters is to have the Avocado's own
test parameters ``self.params`` passed through to the block of code
implementations, either all of them, or a subset based on path.  This
could allow for example, a parameter signaling a "debug" condition to
be passed on to the execution of the block of code.  Example::

  from avocado import Test
  from avocado.streams.code import PythonModule

  class ModuleTest(Test):
    def test(self):
        self.streams[1].run(PythonModule("mymodule",
                                         path=["/opt/myproject"],
                                         params=self.params))

Block of Code Interface for Execution Stream usage
--------------------------------------------------

Another type of public interface, in the sense that it's well known
and documented, is the interface that Execution Stream implementations
will use to interact with Block of Code implementations.  This is not
intended to be used by test writers, though.

Again, it's too early to define a frozen implementation, but this is
how it could look like:

* ``send_self``: uses the Execution Stream's ``send`` interface to properly
  populate the payload or other necessary assets for its execution.
* ``run``: Starts the execution of the payload, and waits for the outcome
  in a synchronous way.  The asynchronous support is handled at the Execution
  Stream side.
* ``success``: Reports the positive or negative outcome in a
  simplistic but precise way.
* ``output``: A dictionary of various outputs that may be generated by the
  execution of the code.  The Execution Stream implementation may merge this
  content with its own ``output`` dictionary, given an unified view of the
  output produced there.

Advanced topics and internals
=============================

Execution Streams
-----------------

An execution stream  was defined as a "disposable execution
environment".  A "disposable execution environment", currently in the
form of a fresh and separate process, is exactly what the Avocado
test runner gives to a test in execution.

While there may be similarities between the Avocado Test Process
(created by the test runner) and execution streams, please note that
the execution streams are created *by* one's test code.  The following
diagram may help to make the roles clearer::

   +-----------------------------------+
   |       Avocado Test Process        |  <= created by the test runner
   | +-------------------------------+ |
   | | main execution stream         | |  <= executes your `test*()` method
   | +-------------------------------+ |
   | | execution stream #1           | |  <= initialized on demand by one's
   | | ...                           | |     test code.  utilities to do so
   | | execution stream #n           | |     are provided by the framework
   | +-------------------------------+ |
   +-----------------------------------+

Even though the proposed mechanism is to let the framework create the
execution lazily (on demand), the use of the execution stream is the
definitive trigger for its creation.  With that in mind, it's accurate
to say that the execution streams are created by one's test code
(running on the "main execution stream").

Synchronous, asynchronous and synchronized execution
----------------------------------------------------

As can be seen in the interface proposal for ``run``, the default
behavior is to have asynchronous executions, as most observed use
cases seem to fit this execution mode.

Still, it may be useful to also have synchronous execution.  For that,
it'd be a matter of setting the ``wait`` option to ``run``.

Another valid execution mode is synchronized execution.  This has been
thoroughly documented by the previous RFCs, under sections named
"Synchronization".  In theory, both synchronous and asynchronous
execution modes could be combined with a synchronized execution, since
the synchronization would happen among the execution streams
themselves.  The synchronization mechanism, usually called a "barrier",
won't be given too much focus here, since on the previous RFCs, it was
considered a somehow agreed and understood point.

Termination
-----------

By favoring asynchronous execution, execution streams need to also
have a default behavior for handling termination of termination
of resources.  For instance, for a process based execution stream,
if the following code is executed::

  from avocado import Test
  from avocado.streams.code import shell
  import time

  class MyTest(avocado.Test):
      def test(self):
          self.streams[0].run(shell("sleep 100"))
          time.sleep(10)

The process created as part of the execution stream would run for
10 seconds, and not 100 seconds.  This reflects that execution streams
are, by definition, **disposable** execution environments.

Execution streams are thus limited to the scope of one test, so
implementations will need to terminate and clean up all associated
resources.

.. note:: based on initial experiments, this will usually mean that a
          ``__del__`` method will be written to handle the cleanup.

Avocado Utility Libraries
-------------------------

Based on initial evaluation, it looks like most of the features necessary
to implement multi stream execution support can be architected as a set
of utility libraries.

One example of pseudo code that could be possible with this design::

  from avocado import Test
  from avocado.streams import get_implementation
  from avocado.streams.code import shell

  class Remote(Test):

      def test_filtering(self):
          klass = get_implementation("remote")
          if klass is not None:
              stream = klass(host=self.params.get("remote_hostname"),
                             username=self.params.get("remote_username")
                             password=self.params.get("remote_password"))
              cmd = "ping -c 1 %s" % self.params.get("test_host_hostname")
              stream.run(shell(cmd))

Please note that this is not the intended end result of this proposal, but
a side effect of implementing it using different software layers.  Most
users should favor the simplified (higher level) interface.

Writing a Multi-Stream test
===========================

As mentioned before, users have not yet been given tools **and
guidelines** for writing multi-host (multi-stream in Avocado lingo)
tests.  By setting a standard and supported way to use the available
tools, we can certainly expect advanced multi-stream tests to become
easier to write and then much more common, robust and better supported
by Avocado itself.

Mapping from parameters
-----------------------

The separation of stream definitions and test is a very important goal
of this proposal.  Avocado already has a advanced parameter system, in
which a test received parameters from various sources.The most common
way of passing parameters at this point is by means of YAML files, so
these will be used as the example format.

Parameters that match a predefined schema (based on paths and node
names) will be by evaluated by a tests' ``streams`` instance
(available as ``self.streams`` within a test).

For instance, the following snippet of test code::

  from avocado import Test

  class MyTest(Test):
      def test(self):
          self.streams[1].run(python("import mylib; mylib.action()"))

Together with the following YAML file fed as input to the parameter
system::

  avocado:
     streams:
      - 1:
          type: remote
          host: foo.example.com

Would result in the execution of ``import mylib; mylib.action()``
in a Python interpreter on host ``foo.example.com``.

If test environments are refered to on a test, but have not been defined
in the outlined schema, Avocado's ``streams`` attribute implementation
can use a default Execution Stream implementation, such as a local process
based one.  This default implementation can, of course, also be configured
at the system and user level by means of configuration files, command line
arguments and so on.

Another possibility is an "execution stream strict mode", in which no
default implementation would be used, but an error condition would be
generated.  This may be useful on environments or tests that are
really tied to their execution stream types.

Intercommunication Test Example
-------------------------------

This is a simple example that exercises the most important aspects
proposed here.  The use case is to check that different hosts can
communicate among themselves.  To do that, we define two streams as
parameters (using YAML here), backed by a "remote" implementation::

  avocado:
     streams:
      - 1:
          type: remote
          host: foo.example.com
      - 2:
          type: remote
          host: bar.example.com

Then, the following Avocado Test code makes use of them::

  from avocado import Test
  from avocado.streams.code import shell

  class InterCommunication(Test):
      def test(self):
          self.streams[1].run(shell("ping -c 1 %s" % self.streams[2].host))
          self.streams[2].run(shell("ping -c 1 %s" % self.streams[1].host))
          self.streams.wait()
          self.assertTrue(self.streams.success)

The ``streams`` attribute provide a aggregated interface for all the streams.
Calling ``self.streams.wait()`` waits for all execution streams (and their
block of code) to finish execution.

Support for slicing, if execution streams names based on integers only could
be added, allowing for writing tests such as::

  avocado:
     streams:
      - 1:
          type: remote
          host: foo.example.com
      - 2:
          type: remote
          host: bar.example.com
      - 3:
          type: remote
          host: blackhat.example.com
      - 4:
          type: remote
          host: pentest.example.com

  from avocado import Test
  from avocado.streams.code import shell

  class InterCommunication(Test):
      def test(self):
          self.streams[1].run(shell("ping -c 1 %s" % self.streams[2].host))
          self.streams[2].run(shell("ping -c 1 %s" % self.streams[1].host))
          self.streams[3].run(shell("ping -c 1 %s" % self.streams[1].host))
          self.streams[4].run(shell("ping -c 1 %s" % self.streams[1].host))
          self.streams.wait()
          self.assertTrue(self.streams[1:2].success)
          self.assertFalse(self.streams[3:4].success)

Support for synchronized execution also maps really well to the
slicing example.  For instance, consider this::

  from avocado import Test
  from avocado.streams.code import shell

  class InterCommunication(Test):
      def test(self):
          self.streams[1].run(shell("ping -c 60 %s" % self.streams[2].host)
          self.streams[2].run(shell("ping -c 60 %s" % self.streams[1].host))
          ddos = shell("ddos --target %s" self.streams[1].host)
          self.streams[3:4].run(ddos, synchronized=True)
          self.streams[1:2].wait()
          self.assertTrue(self.streams.success)

This instructs streams 1 and 2 to start connectivity checks as soon as
they **individually** can, while, for a full DDOS effect, streams 3
and 4 would start only when they are both ready to do so.

Feedback and future versions
============================

This being an RFC, feedback is extremely welcome.  Also, exepect new versions
based on feedback, discussions and further development of the ideas initially
exposed here.
