
#!/usr/bin/env python

""" General tools that are used by multiple python files in this package
"""

################################################################################
#                            PUBLIC MODULE METHODS                             #
################################################################################

def settings_dictionary_is_consistent(SettingsDict):
    """ Make sure dictionary generated from JSON settings file conforms to MARBL
        parameter file standards:
        1. _order is a top-level key
        2. Everything listed in _order is a top-level key
        3. All top-level keys that do not begin with '_' are listed in _order
        4. All second-level dictionaries (variable names) contain datatype key
        5. If datatype is not a dictionary, variable dictionary keys also included
           longname, subcategory, units, default_value
        6. If datatype is a dictionary, all keys in the datatype are variables per (5)
        7. In a variable (or datatype entry) where default_value is a dictionary,
           "default" is a key
        NOTE: (7) is checked explicitly along with (5) and (6) in _valid_variable_dict()
    """

    import logging
    logger = logging.getLogger(__name__)
    invalid_file = False

    # 1. _order is a top-level key
    if "_order" not in SettingsDict.keys():
        logger.error("Can not find _order key")
        return True

    # 2. Everything listed in _order is a top-level key
    for cat_name in SettingsDict["_order"]:
        if cat_name not in SettingsDict.keys():
            logger.error("Can not find %s category that is listed in _order" % cat_name)
            invalid_file = True

    for cat_name in SettingsDict.keys():
        if cat_name[0] != '_':
        # 3. All top-level keys that do not begin with '_' are listed in _order
            if cat_name not in SettingsDict["_order"]:
                logger.error("Category %s not included in _order" % cat_name)
                invalid_file = True

            # 4. All second-level dictionaries (variable names) contain datatype key
            #    If the variable is of a derived type, then datatype is a dictionary itself
            for var_name in SettingsDict[cat_name].keys():
                if "datatype" not in SettingsDict[cat_name][var_name].keys():
                    logger.error("Variable %s does not contain a key for datatype" % var_name)
                    invalid_file = True
                    continue

                if not isinstance(SettingsDict[cat_name][var_name]["datatype"], dict):
                    # 5. If datatype is not a dictionary, variable dictionary keys should include
                    #    longname, subcategory, units, datatype, default_value
                    #    Also, if default_value is a dictionary, that dictionary needs to contain "default" key
                    if not _valid_variable_dict(SettingsDict[cat_name][var_name], var_name):
                        invalid_file = True
                else:
                    # 6. If datatype is a dictionary, all keys in the datatype are variables per (5)
                    for subvar_name in SettingsDict[cat_name][var_name]["datatype"].keys():
                        if subvar_name[0] != '_':
                            if not _valid_variable_dict(SettingsDict[cat_name][var_name]["datatype"][subvar_name],
                                                        "%s%%%s"  % (var_name, subvar_name)):
                                invalid_file = True

    return (not invalid_file)

################################################################################

def diagnostics_dictionary_is_consistent(DiagsDict):
    """ Make sure dictionary generated from JSON settings file conforms to MARBL
        diagnostics file standards:
        1. All top-level keys refer to diagnostic variable
        2. All diagnostic variable dictionaries contain the following keys:
           i.   module
           ii.  longname
           iii. units
           iv.  vertical_grid (2D vars should explicitly list "none")
           v.   frequency
           vi.  operator
        3. Consistency between frequency and operator
           i.   frequency and operator are both lists, or neither are
           ii.  If they are both lists, must be same size
        4. Allowable frequencies are never, low, medium, and high
        5. Allowable operators are instantaneous, average, minimum, and maximum
    """

    import logging
    logger = logging.getLogger(__name__)
    invalid_file = False

    if not isinstance(DiagsDict, dict):
        logger.error("Argument must be a dictionary")
        return False

    # 2. All diagnostic variable dictionaries contain the following keys:
    for diag_name in DiagsDict.keys():
        if not isinstance(DiagsDict[diag_name], dict):
            logger.error("DiagsDict['%s'] must be a dictionary" % diag_name)
            invalid_file = True
            continue

        diag_subkeys = DiagsDict[diag_name].keys()
        bad_diag_name_dict = False
        for required_field in ['module', 'longname', 'units', 'vertical_grid', 'frequency', 'operator']:
            if required_field not in diag_subkeys:
                logger.error("%s not a key in DiagsDict['%s']" % (required_field, diag_name))
                invalid_file = True
                bad_diag_name_dict = True
        if bad_diag_name_dict:
            continue

        # 3. Consistency between frequency and operator
        err_prefix = "Inconsistency in DiagsDict['%s']:" % diag_name
        #    i.   frequency and operator are both lists, or neither are
        if isinstance(DiagsDict[diag_name]['frequency'], list) != isinstance(DiagsDict[diag_name]['operator'], list):
            logger.error("%s either both frequency and operator must be lists or neither can be" % err_prefix)

        #    ii.  If they are both lists, must be same size
        if isinstance(DiagsDict[diag_name]['frequency'], list):
            freq_len = len(DiagsDict[diag_name]['frequency'])
            op_len = len(DiagsDict[diag_name]['operator'])
        else:
            freq_len = 1
            op_len = 1
        if freq_len != op_len:
            logger.error("%s frequency is length %d but operator is length %d" %
                         (err_prefix, diag_name, freq_len, op_len))
            invalid_file = True
            continue

        # 4. Allowable frequencies are never, low, medium, and high
        # 5. Allowable operators are instantaneous, average, minimum, and maximum
        ok_freqs = ['never', 'low', 'medium', 'high']
        ok_ops = ['instantaneous', 'average', 'minimum', 'maximum']
        if isinstance(DiagsDict[diag_name]['frequency'], list):
            for n, freq in enumerate(DiagsDict[diag_name]['frequency']):
                op = DiagsDict[diag_name]['operator'][n]
                if freq not in ok_freqs:
                    logger.error("%s '%s' is not a valid frequency" % (err_prefix, freq))
                    invalid_file = True
                if op not in ok_ops:
                    logger.error("%s '%s' is not a valid operator" % (err_prefix, op))
                    invalid_file = True
        else:
            freq = DiagsDict[diag_name]['frequency']
            op = DiagsDict[diag_name]['operator']
            if freq not in ok_freqs:
                logger.error("%s '%s' is not a valid frequency" % (err_prefix, freq))
                invalid_file = True
            if op not in ok_ops:
                logger.error("%s '%s' is not a valid operator" % (err_prefix, op))
                invalid_file = True

    return (not invalid_file)

################################################################################
#                            PRIVATE MODULE METHODS                            #
################################################################################

def _valid_variable_dict(var_dict, var_name):
    """ Return False if dictionary does not contain any of the following:
        * longname
        * subcategory
        * units
        * datatype
        * default_value
    """

    import logging
    logger = logging.getLogger(__name__)
    for key_check in ["longname", "subcategory", "units", "datatype", "default_value"]:
        if key_check not in var_dict.keys():
            message = "Variable %s is not well-defined in YAML" % var_name
            message = message + "\n     * Expecting %s as a key" % key_check
            logger.error(message)
            return False
    if isinstance(var_dict["default_value"], dict):
        # Make sure "default" is a valid key if default_value is a dictionary
        if "default" not in var_dict["default_value"].keys():
            logger.error("default_value dictionary in variable %s must have 'default' key" % var_name)
            logger.info("Keys in default_value are %s" % var_dict["default_value"].keys())
            return False
    return True

################################################################################
