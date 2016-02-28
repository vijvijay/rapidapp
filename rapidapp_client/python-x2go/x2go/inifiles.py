# -*- coding: utf-8 -*-

"""\
X2GoProcessIniFile - helper class for parsing .ini files

"""
__NAME__ = 'x2goinifiles-pylib'

# modules
import os
import ConfigParser
import types
import cStringIO
import copy

# Python X2Go modules
from defaults import LOCAL_HOME as _current_home
import log
import utils

class X2GoIniFile(object):
    """
    Base class for processing the different ini files used by X2Go
    clients. Primarily used to standardize the content of the different
    X2Go client ini file (settings, printing, sessions, xconfig).

    If entries are omitted in an ini file, they are filled with
    default values (as hard coded in Python X2Go), so the resulting objects 
    always contain the same fields.

    """

    def __init__(self, config_files, defaults=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param config_files: a list of configuration file names (e.g. a global filename and a user's home
            directory filename)
        @type config_files: C{list}
        @param defaults: a cascaded Python dicitionary structure with ini file defaults (to override
            Python X2Go's hard coded defaults in L{defaults}
        @type defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoIniFile} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.user_config_file = None
        self._write_user_config = True

        # make sure a None type gets turned into list type
        if not config_files:
            config_files = []

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.config_files = config_files

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

        _create_file = False
        for file_name in self.config_files:
            file_name = os.path.normpath(file_name)
            if file_name.startswith(_current_home):
                if not os.path.exists(file_name):
                    utils.touch_file(file_name)
                    _create_file = True
                self.user_config_file = file_name
                break
        self.load()

        if _create_file:
            self._write_user_config = True
            self._X2GoIniFile__write()

    def load(self):
        """\
        R(e-r)ead configuration file(s).

        """
        self.logger('proposed config files are %s' % self.config_files, loglevel=log.loglevel_INFO, )
        _found_config_files = self.iniConfig.read(self.config_files)
        self.logger('config files found: %s' % _found_config_files or 'none', loglevel=log.loglevel_INFO, )

        for file_name in _found_config_files:
            if file_name.startswith(os.path.normpath(_current_home)):
                # we will use the first file found in the user's home dir for writing modifications
                self.user_config_file = file_name
                break

        self.config_files = _found_config_files
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
        if self.user_config_file and self._write_user_config:
            try:
                fd = open(self.user_config_file, 'wb')
                self.iniConfig.write(fd)
                fd.close()
                self._write_user_config = False
                return True
            except Exception, e:
                print e
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
