# Studies examples

1. [Retain an incomplete study draft](01_portable_study.ipynb) uses only Studies'
   own portable specification and I/O. It needs no engines, weather or database.
   The embedded workflow remains explicitly incomplete until its owner validates
   execution inputs.
2. [Engine comparison fixtures](engine_comparison/README.md) require compatible
   Core/RC installations and the declared EnergyPlus executable. This existing
   research fixture runner remains supported. Reusable prepared execution and
   result collection now live in Workflows and Studies; application acceptance
   harnesses should call those public APIs.

Notebooks run from fresh kernels against installed packages. Numerical agreement
between fixture engines does not establish empirical prediction accuracy.
