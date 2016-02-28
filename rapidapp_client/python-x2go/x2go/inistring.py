# -*- coding: utf-8 -*-

"""\
X2GoIniString - helper class for parsing strings whose.ini file 

"""
__NAME__ = 'x2goinistring-pylib'

# modules
import os
import ConfigParser
import types
import cStringIO
import StringIO
import copy

# Python X2Go modules
from defaults import LOCAL_HOME as _current_home
import log
import utils

class X2GoIniString(object):
    """
    Base class for processing the different ini files used by X2Go
    clients. Primarily used to standardize the content of the different
    X2Go client ini file (settings, printing, sessions, xconfig).

    If entries are omitted in an ini file, they are filled with
    default values (as hard coded in Python X2Go), so the resulting objects 
    always contain the same fields.

    """

    def __init__(self, config_file_string, defaults=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param config_file_string: contents of the inifile to be loaded
        @type config_file_string: C{string}
        @param defaults: a cascaded Python dicitionary structure with ini file defaults (to override
            Python X2Go's hard coded defaults in L{defaults}
        @type defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoIniString} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.user_config_file = None
        self._write_user_config = True
        self.config_string = config_file_string

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        if utils._checkIniFileDefaults(defaults):
            self.defaultValues = defaults
        else:
            self.defaultValues = {}

        # we purposefully do not inherit the SafeConfigParser class
        # here as we do not want to run into name conflicts between
        # X2Go ini file options and method / property names in
        # SafeConfigParser... This is a pre-cautious approach...
        self.iniConfig = ConfigParser.SafeConfigParser()
        self.iniConfig.optionxform = str

        self.load()

    def load(self):
        """\
        R(e-r)ead configuration file(s).

        """
        buf = StringIO.StringIO(self.config_string)
        self.iniConfig.readfp(buf)

        self._fill_defaults()

    def __repr__(self):
        result = 'X2GoIniFile('
        for p in dir(self):
            if '__' in p or not p in self.__dict__ or type(p) is types.InstanceType: continue
            result += p + '=' + str(self.__dict__[p]) + ','
        result = result.strip(',')
        return result + ')'

    def _storeValue(self, section, key, value):
        """\
        Stores a value for a given section and key.

        This methods affects a SafeConfigParser object held in
        RAM. No configuration file is affected by this 
        method. To write the configuration to disk use
        the L{write()} method.

        @param section: the ini file section
        @type section: C{str}
        @param key: the ini file key in the given section
        @type key: C{str}
        @param value: the value for the given section and key
        @type value: C{str}, C{list}, C{booAl}, ...

        """
        if type(value) == type(u''):
            value = value.encode(utils.get_encoding())
        if type(value) is types.BooleanType:
            self.iniConfig.set(section, key, str(int(value)))
        elif type(value) in (types.ListType, types.TupleType):
            self.iniConfig.set(section, key, ", ".join(value))
        else:
            self.iniConfig.set(section, key, str(value))

    def _fill_defaults(self):
        """\
        Fills a C{SafeConfigParser} object with the default ini file 
        values as pre-defined in Python X2Go or. This SafeConfigParser 
        object is held in RAM. No configuration file is affected by this 
        method.

        """
        for section, sectionvalue in self.defaultValues.items():
            for key, value in sectionvalue.items():
                if self.iniConfig.has_option(section, key): continue
                if not self.iniConfig.has_section(section):
                    self.iniConfig.add_section(section)
                self._storeValue(section, key, value)

    def update_value(self, section, key, value):
        """\
        Change a value for a given section and key. This method
        does not have any effect on configuration files.

        @param section: the ini file section
        @type section: C{str}
        @param key: the ini file key in the given section
        @type key: C{str}
        @param value: the value for the given section and key
        @type value: C{str}, C{list}, C{bool}, ...

        """
        if not self.iniConfig.has_section(section):
            self.iniConfig.add_section(section)
        self._storeValue(section, key, value)
        self._write_user_config = True
    __update_value = update_value

    def write(self):
        """\
        Write the ini file modifications (SafeConfigParser object) from RAM to disk.

        For writing the first of the C{config_files} specified on instance construction
        that is writable will be used.

        @return: C{True} if the user config file has been successfully written, C{False} otherwise.
        @rtype: C{bool}

        """
        #Apprime: Can't write to iniString
        self.logger('Apprime ==>> Can\'t write to config iniStrings. Did you think this is a config FILE???' , loglevel=log.loglevel_INFO, )
        self.logger('Apprime ==>> Attempted write config: %s' % self.printable_config_file, loglevel=log.loglevel_INFO, )
        return False 
    __write = write

    def get_type(self, section, key):
        """\
        Retrieve a value type for a given section and key. The returned
        value type is based on the default values dictionary.

        @param section: the ini file section
        @type section: C{str}
        @param key: the ini file key in the given section
        @type key: C{str}

        @return: a Python variable type
        @rtype: class

        """
        return type(self.defaultValues[section][key])

    def get_value(self, section, key, key_type=None):
        """\
        Retrieve a value for a given section and key.

        @param section: the ini file section
        @type section: C{str}
        @param key: the ini file key in the given section
        @type key: C{str}

        @return: the value for the given section and key
        @rtype: class

        """
        if key_type is None:
            key_type = self.get_type(section, key)
        if self.iniConfig.has_option(section, key):
            if key_type is types.BooleanType:
                return self.iniConfig.getboolean(section, key)
            elif key_type is types.IntType:
                return self.iniConfig.getint(section, key)
            elif key_type is types.ListType:
                _val = self.iniConfig.get(section, key)
                _val = _val.strip()
                if _val.startswith('[') and _val.endswith(']'):
                    return eval(_val)
                elif ',' in _val:
                    _val = [ v.strip() for v in _val.split(',') ]
                else:
                    _val = [ _val ]
                return _val
            else:
                _val = self.iniConfig.get(section, key)
                return _val.decode(utils.get_encoding())
    get = get_value
    __call__ = get_value

    @property
    def printable_config_file(self):
        """\
        Returns a printable configuration file as a multi-line string.

        """
        stdout = cStringIO.StringIO()
        self.iniConfig.write(stdout)
        _ret_val = stdout.getvalue()
        stdout.close()
        return _ret_val
