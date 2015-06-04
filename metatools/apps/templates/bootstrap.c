#include <Python.h>


int main(int argc, char **argv) {

    // Disable importing the site module. We will manually import it in
    // the bootstrapper, but we want to be able to modify sys.path before
    // site runs (which imports a few WesternX packages that we may want
    // to override via sys.path).
    Py_NoSiteFlag = 1;
    
    Py_SetProgramName(argv[0]);
    Py_Initialize();

    PySys_SetArgvEx(argc, argv, 0);
    PyRun_SimpleString(
        #ifdef METATOOLS_BOOTSTRAP_SOURCE
            METATOOLS_BOOTSTRAP_SOURCE
        #else
            "print 'Compiled without METATOOLS_BOOTSTRAP_SOURCE.'"
        #endif
    );
    
    Py_Finalize();
    return 0;

}
