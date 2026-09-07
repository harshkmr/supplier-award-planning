/*
 * _container_util.c — CPython C extension for container utilization scoring.
 *
 * Exports:
 *   score_utilization(cargo_weight_kg, tare_weight_kg, max_gross_kg) -> float
 *
 * Returns the fraction of usable payload consumed by the cargo:
 *   utilization = cargo_weight_kg / (max_gross_kg - tare_weight_kg)
 *
 * Raises:
 *   ValueError  — if any weight is negative, or max_gross_kg <= tare_weight_kg
 *   OverflowError — if utilization > 1.0 (cargo exceeds payload capacity)
 *
 * Design goals:
 *   - Correct reference counting on every code path
 *   - No memory leaks (Valgrind-clean)
 *   - Compile cleanly with -Wall -Wextra -Werror
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
score_utilization(PyObject *self, PyObject *args)
{
    double cargo_weight_kg;
    double tare_weight_kg;
    double max_gross_kg;
    double payload_capacity;
    double utilization;

    (void)self;  /* suppress unused-parameter warning on GCC/Clang/MSVC */

    /* Parse three doubles from Python arguments */
    if (!PyArg_ParseTuple(args, "ddd", &cargo_weight_kg,
                          &tare_weight_kg, &max_gross_kg)) {
        return NULL;  /* PyArg_ParseTuple already set TypeError */
    }

    /* Validate: no negative weights */
    if (cargo_weight_kg < 0.0) {
        PyErr_SetString(PyExc_ValueError,
                        "cargo_weight_kg must be non-negative");
        return NULL;
    }
    if (tare_weight_kg < 0.0) {
        PyErr_SetString(PyExc_ValueError,
                        "tare_weight_kg must be non-negative");
        return NULL;
    }
    if (max_gross_kg < 0.0) {
        PyErr_SetString(PyExc_ValueError,
                        "max_gross_kg must be non-negative");
        return NULL;
    }

    /* Validate: max_gross must exceed tare for a positive payload */
    payload_capacity = max_gross_kg - tare_weight_kg;
    if (payload_capacity <= 0.0) {
        PyErr_SetString(PyExc_ValueError,
                        "max_gross_kg must be greater than tare_weight_kg");
        return NULL;
    }

    /* Compute utilization */
    utilization = cargo_weight_kg / payload_capacity;

    /* Validate: utilization must not exceed 1.0 (overweight) */
    if (utilization > 1.0) {
        PyErr_SetString(PyExc_OverflowError,
                        "cargo exceeds container payload capacity "
                        "(utilization > 1.0)");
        return NULL;
    }

    /* Return a Python float — PyFloat_FromDouble returns a new reference */
    return PyFloat_FromDouble(utilization);
}

/* Method table */
static PyMethodDef ContainerUtilMethods[] = {
    {
        "score_utilization",
        score_utilization,
        METH_VARARGS,
        "score_utilization(cargo_weight_kg, tare_weight_kg, max_gross_kg)\n"
        "\n"
        "Compute container utilization as a fraction of payload capacity.\n"
        "\n"
        "Parameters\n"
        "----------\n"
        "cargo_weight_kg : float\n"
        "    Weight of the cargo in kilograms (>= 0).\n"
        "tare_weight_kg : float\n"
        "    Empty weight of the container in kilograms (>= 0).\n"
        "max_gross_kg : float\n"
        "    Maximum gross weight of the container in kilograms.\n"
        "    Must be greater than tare_weight_kg.\n"
        "\n"
        "Returns\n"
        "-------\n"
        "float\n"
        "    Utilization in [0.0, 1.0].\n"
        "\n"
        "Raises\n"
        "------\n"
        "ValueError\n"
        "    If any weight is negative or max_gross_kg <= tare_weight_kg.\n"
        "OverflowError\n"
        "    If utilization > 1.0 (cargo exceeds payload capacity).\n"
    },
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

/* Module definition */
static struct PyModuleDef containerutilmodule = {
    PyModuleDef_HEAD_INIT,
    "_container_util",
    "CPython C extension for ISO container utilization scoring.\n"
    "\n"
    "Designed to be Valgrind-clean: correct reference counting,\n"
    "no memory leaks, proper error handling on every code path.",
    -1,
    ContainerUtilMethods
};

/* Module initialisation */
PyMODINIT_FUNC
PyInit__container_util(void)
{
    return PyModule_Create(&containerutilmodule);
}
