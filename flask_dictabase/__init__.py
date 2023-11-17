import json
import pickle
import time
import datetime
import dataset
from flask import current_app, _app_ctx_stack
import operator

DEBUG = False


class Dictabase:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.app.app_context()
        self.logger = None
        self.var = VariableManager(self)

    def print(self, *args):
        if self.logger:
            self.logger(f'{datetime.datetime.now()}: ' + ' '.join(str(a) for a in args))

    def init_app(self, app):
        app.config.setdefault('DATABASE_URL', 'sqlite:///dictabase.db')
        app.teardown_appcontext(self.teardown)

    def _GetDB(self):
        return dataset.connect(
            self.app.config['DATABASE_URL'],
            engine_kwargs={'connect_args': {'check_same_thread': False}} if 'sqlite' in self.app.config[
                'DATABASE_URL'] else None,
        )

    @property
    def db(self):
        ctx = _app_ctx_stack.top
        self.print('_app_ctx_stack.top=', ctx)
        if ctx is not None:
            if not hasattr(ctx, 'db'):
                # create a new db connection and attach it to this context
                ctx.db = self._GetDB()
                with ctx.db.lock:
                    ret = ctx.db
                    self.print('return with ctx.db.lock=', ret)
                    return ret

            self.print('return ctx.db=', ctx.db)
            return ctx.db

        raise RuntimeError(
            'No AppContext found. You probably tried to access this database from outside a request context (aka outside a View function). Try using "with app.app_context(): DoThing()" instead.')

    def teardown(self, exception):
        try:
            self.db.close()
        except:
            pass

    def FindAll(self, cls, **kwargs):
        """
        You can paginate by passing {'_offset': int(number)} in kwargs.
        You can limit the number of results by passing {'_limit': int(howmany)} in kwargs.
        You can reverse the order of results by passing {'_reverse: True} in kwargs.
        You can order the results by a column by passing {'_orderBy': str(columnName)} in kwargs.

        :param cls:
        :param kwargs:
        :return: generator, yields BaseTable-subclass objects
        """
        tableName = cls if isinstance(cls, str) else cls.__name__

        args = []
        # handle the _where keywords
        i = 1
        while True:
            # the user can have multiple '_where' statements
            # each group is designated by a different number of preceeding '_'
            # example:
            # ret = app.db.FindAll(
            #     Person,
            #     _where='birth_month',
            #     _equals=3,
            #
            #     __where='birth_day',
            #     __equals=11,
            # )
            where = kwargs.pop('_' * i + 'where', None)
            lessThan = kwargs.pop('_' * i + 'lessThan', None)
            lessThanOrEqualTo = kwargs.pop('_' * i + 'lessThanOrEqualTo', None)
            greaterThan = kwargs.pop('_' * i + 'greaterThan', None)
            greaterThanOrEqualTo = kwargs.pop('_' * i + 'greaterThanOrEqualTo', None)
            equals = kwargs.pop('_' * i + 'equals', None)

            if where:
                if lessThan:
                    args.append(getattr(self.db[tableName].table.columns, where) < lessThan)
                if lessThanOrEqualTo:
                    args.append(getattr(self.db[tableName].table.columns, where) <= lessThanOrEqualTo)
                if greaterThan:
                    args.append(getattr(self.db[tableName].table.columns, where) > greaterThan)
                if greaterThanOrEqualTo:
                    args.append(getattr(self.db[tableName].table.columns, where) >= greaterThanOrEqualTo)
                if equals:
                    args.append(getattr(self.db[tableName].table.columns, where) == equals)
            else:
                break
            i += 1

        # handle the other keywords
        reverse = kwargs.pop('_reverse', False)  # bool
        orderBy = kwargs.pop('_orderBy', None)  # str
        if reverse is True:
            if orderBy is not None:
                orderBy = '-' + orderBy
            else:
                orderBy = '-id'

        if orderBy is not None:
            with self.db.lock:
                self.WaitForTransactionsToComplete()
                for obj in self.db[tableName].find(
                        *args,
                        order_by=[f'{orderBy}'],
                        **kwargs
                ):
                    yield cls(db=self, app=self.app, **obj)
        else:
            with self.db.lock:
                self.WaitForTransactionsToComplete()
                for obj in self.db[tableName].find(*args, **kwargs):
                    yield cls(db=self, app=self.app, **obj)

    def WaitForTransactionsToComplete(self, timeout=5):
        startTime = time.time()
        while time.time() - startTime < timeout:
            if not self.db.in_transaction:
                break
            time.sleep(0.1)

    def FindOne(self, cls, **kwargs):
        tableName = cls if isinstance(cls, str) else cls.__name__

        with self.db.lock:
            self.WaitForTransactionsToComplete()
            ret = self.db[tableName].find_one(**kwargs)

        if ret:
            ret = cls(db=self, app=self.app, **ret)
            return ret
        else:
            return None

    def New(self, cls, **kwargs):
        tableName = cls if isinstance(cls, str) else cls.__name__

        ret = None
        with self.db.lock:
            self.WaitForTransactionsToComplete()
            self.db.begin()
            newID = self.db[tableName].insert(dict(**kwargs))
            self.db.commit()
            ret = cls(db=self, app=self.app, id=newID, **kwargs)
        return ret

    def NewOrFind(self, cls, **kwargs):
        # Looks in the database for an existing object, if none, create a new row and return it
        ret = self.FindOne(cls, **kwargs)
        if ret:
            return ret  # an object exist already, return it
        else:
            return self.New(cls, **kwargs)  # create a new object and return it

    def Upsert(self, obj):
        ret = None
        with self.db.lock:
            self.WaitForTransactionsToComplete()
            self.db.begin()
            ret = self.db[type(obj).__name__].upsert(dict(obj), ['id'])
            self.db.commit()
        return ret

    def Delete(self, obj):
        # break all links first
        for item in obj.Links():
            obj.Unlink(item)

        ret = None
        with self.db.lock:
            self.WaitForTransactionsToComplete()
            self.db.begin()
            ret = self.db[type(obj).__name__].delete(id=obj['id'])
            self.db.commit()
        return ret

    def Drop(self, cls, confirm=False):
        tableName = cls if isinstance(cls, str) else cls.__name__

        if confirm is False:
            raise Exception('You must pass confirm=True to Drop a table.')
        with self.db.lock:
            self.WaitForTransactionsToComplete()
            self.db.begin()
            ret = self.db[tableName].drop()
            self.db.commit()
        return ret


class BaseTable(dict):

    def __init__(self, *a, **k):
        self.db = k.pop('db')
        self.app = k.pop('app')
        super().__init__(*a, **k)

    def Commit(self):
        ret = self.db.Upsert(self)
        return ret

    def __setitem__(self, *a, **k):
        super().__setitem__(*a, **k)
        self.Commit()

    def update(self, *a, **k):
        super().update(*a, **k)
        self.Commit()

    def Update(self, d):
        # same as update, but accounts converts value of type list/dict to json
        for k, v in d.items():
            if isinstance(v, (list, dict)):
                self.Set(k, v)
            else:
                self[k] = v

    def __str__(self):
        '''

        :return: string like '<BaseTable: email=me@website.com(type=str), name=John(type=str), age=33(type=int)>'
        '''
        itemsList = []
        for k, v, in self.items():
            if k.startswith('_'):
                if DEBUG is False:
                    continue  # dont print these

            if isinstance(v, str) and len(v) > 25:
                v = v[:25] + '...'
            itemsList.append(('{}={}(type={})'.format(k, v, type(v).__name__)))

        if DEBUG:
            itemsList.append(('{}={}'.format('pyid', id(self))))

        return '<{}: {}>'.format(
            type(self).__name__,
            ', '.join(itemsList)
        )

    def __repr__(self):
        return str(self)

    def Get(self, key, default=None, loader=json.loads):
        value = self.get(key, None)
        if value:
            value = loader(value)
        else:
            value = default
        return value

    def Set(self, key, value, dumper=json.dumps, dumperKwargs={'indent': 2, 'sort_keys': True}):
        value = dumper(value, **dumperKwargs)
        self[key] = value
        self.Commit()

    def Remove(self, key, value, removeAll=False):
        """

        :param key:
        :param value:
        :param removeAll: bool > if True, will remove all matching values
        :return:
        """
        the_list = self.Get(key, [])
        while value in the_list:
            the_list.remove(value)
            if not removeAll:
                break
        self.Set(key, the_list)

    def Append(self, key, value, allowDuplicates=True):
        '''
        Usage:
            self.Append('items', item)

        Is equal to:
            items = self.Get('items', [])
            items.append(item)
            self.Set('items', items)

        :param key:
        :param value:
        :param allowDuplicates: bool > True means the list can contain duplicates
        :return:
        '''
        items = self.Get(key, [])
        if allowDuplicates is False and value in items:
            return
        else:
            items.append(value)
            self.Set(key, items)

    def SetItem(self, key, subKey, value):
        '''
        Usage:
            self.SetItem(key, subKey, value)

        Is equal to:
            items = self.Get(key, {})
            items[subKey] = value
            self.Set(key, items)

        :param key:
        :param value:
        :return:
        '''
        items = self.Get(key, {})
        items[subKey] = value
        self.Set(key, items)

    def GetItem(self, key, subkey, default=None):
        d = self.Get(key, {})
        ret = d.get(subkey, default)
        return ret

    def PopItem(self, key, subkey, default=None):
        d = self.Get(key, {})
        ret = d.pop(subkey, default)
        self.Set(key, d)
        return ret

    @property
    def Count(self):
        """

        :return: int, total number of rows for this table
        """
        tableName = type(self).__name__
        return self.db[tableName].count()

    def Link(self, obj, doubleLink=True):
        linkList = self.Get('_links', [], loader=pickle.loads)
        d = {
            'class': type(obj),
            'id': obj['id'],
        }
        if d not in linkList:  # no duplicates please
            linkList.append(d)

        self.Set('_links', linkList, dumper=pickle.dumps, dumperKwargs={})

        if doubleLink:
            obj.Link(self, doubleLink=False)

    def Unlink(self, obj, doubleUnlink=True):
        linkList = self.Get('_links', [], loader=pickle.loads)
        d = {
            'class': type(obj),
            'id': obj['id'],
        }
        if d in linkList:  # no duplicates please
            linkList.remove(d)

        self.Set('_links', linkList, dumper=pickle.dumps, dumperKwargs={})

        if doubleUnlink:
            obj.Unlink(self, doubleUnlink=False)

    def Links(self, cls=None, **kwargs):
        linkList = self.Get('_links', [], loader=pickle.loads)
        for item in linkList:
            if item['class'] == cls or cls is None:
                obj = self.db.FindOne(cls or item['class'], id=item['id'])
                if obj:
                    for k, v in kwargs.items():
                        if obj[k] != v:
                            break
                    else:
                        yield obj


class VariableManager:
    def __init__(self, db):
        self.db = db

    def Set(self, name, value):
        v = self.db.FindOne(Var, name=name)
        if v is None:
            v = self.db.New(Var, name=name)
        v.Set('value', value)

    def Get(self, name, default=None):
        v = self.db.FindOne(Var, name=name)
        if v is None:
            v = self.db.New(Var, name=name)
        return v.Get('value', default)


class Var(BaseTable):
    pass
