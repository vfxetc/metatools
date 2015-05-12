#include <Python.h>


int main(int argc, char **argv) {

    Py_SetProgramName(argv[0]);
    Py_Initialize();

    PyObject *myArgv = PyList_New(argc);
    for (int i = 0; i < argc; i++) {
        PyList_SET_ITEM(myArgv, i, PyString_FromString(argv[i]));
    }
    PySys_SetObject("argv", myArgv);

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
