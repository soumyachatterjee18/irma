#
# Copyright (c) 2014 QuarksLab.
# This file is part of IRMA project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the top-level directory
# of this distribution and at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# No part of the project, including this file, may be copied,
# modified, propagated, or distributed except according to the
# terms contained in the LICENSE file.


from sqlalchemy import update
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from irma.common.exceptions import IrmaValueError, IrmaDatabaseResultNotFound
from irma.database.sqlhandler import SQLDatabase
from irma.common.exceptions import IrmaDatabaseError


def session_maker(func):
    """Annotation that provides a session if needed
    """
    def wrapper(*args, **kwargs):
        if 'session' not in kwargs.keys():
            kwargs['session'] = SQLDatabase.get_session()
            session_created = True
        else:
            session_created = False

        func_ret = func(*args, **kwargs)

        if session_created:
            kwargs['session'].commit()

        return func_ret

    return wrapper


class SQLDatabaseObject(object):
    """Mother class for the SQL tables
    """

    __tablename__ = None

    _fields_suffix = None
    _idname = None

    # Fields
    # In the subclasses, the variables names must be the same has fields
    # names without the suffix except for the foreign keys and PFKs
    # Ex for a PK or field : var name: some_field
    #                        field name: some_field_suffix
    # Ex for a FK or PFK : var name: some_key
    #                      key name: some_key
    id = None

    def __init__(self):
        if type(self) is SQLDatabaseObject:
            reason = "The SQLDatabaseObject class has to be overloaded"
            raise IrmaValueError(reason)

    def to_dict(self, include_pks=True, include_fks=True):
        """Converts object to dict.
        :rtype: dict
        """
        res = {}
        columns_list = []
        for column in self.__table__.columns:
            # table name removal (fixed length)
            columns_list.append(str(column)[len(self.__tablename__ + '.'):])

        pk_names_list = []
        if not include_pks:
            for pk in self.__mapper__.primary_key:
                pk_names_list.append(pk.name)

        fk_names_list = []
        if not include_fks:
            for fk in self.__table__.foreign_keys:
                # table name removal (various length)
                fk_names_list.append(fk.target_fullname.rsplit('.', 1)[1])

        for key in columns_list:
            var_name_list = key.rsplit('_', 1)    # field suffix removal
            var_name = var_name_list[0] \
                if '_'+var_name_list[1] == self._fields_suffix else key

            if getattr(self, var_name) is not None:
                if (not include_pks and key in pk_names_list) or\
                        (not include_fks and key in fk_names_list):
                    continue
                res[key] = getattr(self, var_name)
        return res

    @session_maker
    def update(self, update_dict=[], session=None):
        """Save the new state of the current object in the database
        :param update_dict: the fields to update (all fields are being
            updated if not provided)
        :param session: the session to use (automatically provided if None)
        """
        if not update_dict:
            update_dict = self.to_dict(include_pks=False)
        session.execute(
            update(self.__class__).where(
                self.__class__.id == self.id
            ).values(update_dict)
        )

    @session_maker
    def save(self, session=None):
        """Save the current object in the database
        :param session: the session to use (automatically provided if None)
        """
        session.add(self)

    @classmethod
    @session_maker
    def load(cls, id, session=None):
        """Load an object from the database
        :param id: the id to look for
        :param session: the session to use (automatically provided if None)
        :rtype: cls
        :return: the object that corresponds to the id
        :raise IrmaDatabaseResultNotFound: if the object doesn't exist
        """
        try:
            return cls.find_by_id(id, session=session)
        except Exception:
            raise IrmaDatabaseResultNotFound(
                "The given id ({0}) doesn't exist in {1}".format(
                    id, cls.__tablename__
                )
            )

    @session_maker
    def remove(self, session=None):
        """Remove the current object from the database
        :param session: the session to use (automatically provided if None)
        """
        session.delete(self)

    @classmethod
    @session_maker
    def find_by_id(cls, id, session=None):
        """Find the object in the database
        :param id: the id to look for
        :param session: the session to use (automatically provided if None)
        :rtype: cls
        :return: the object that corresponds to the id
        :raise IrmaDatabaseResultNotFound, IrmaDatabaseError
        """
        try:
            return session.query(cls).filter(
                cls.id == id
            ).one()
        except NoResultFound as e:
            raise IrmaDatabaseResultNotFound(e)
        except MultipleResultsFound as e:
            raise IrmaDatabaseError(e)

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return str(self.to_dict())
