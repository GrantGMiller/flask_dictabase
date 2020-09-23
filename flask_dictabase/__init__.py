import json
import time

import dataset
from flask import current_app, _app_ctx_stack

DEBUG = False


class Dictabase:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.app.app_context()

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
        if ctx is not None:
            if not hasattr(ctx, 'db'):
                ctx.db = self._GetDB()
                with ctx.db.lock:
                    return ctx.db
            return ctx.db
        return self._GetDB()

    def teardown(self, exception):
        try:
            self.db.close()
        except:
            pass

    def FindAll(self, cls, **kwargs):
        tableName = cls if isinstance(cls, str) else cls.__name__

        reverse = kwargs.pop('_reverse', False)  # bool
        orderBy = kwargs.pop('_orderBy', None)  # str
        if reverse is True:
            if orderBy is not None:
                orderBy = '-' + orderBy
            else:
                orderBy = '-id'

        if orderBy is not None:
            with self.db.lock:
                for obj in self.db[tableName].find(
                        order_by=[f'{orderBy}'],
                        **kwargs
                ):
                    yield cls(db=self, app=self.app, **obj)
        else:
            with self.db.lock:
                for obj in self.db[tableName].find(**kwargs):
                    yield cls(db=self, app=self.app, **obj)

    def FindOne(self, cls, **kwargs):
        tableName = cls if isinstance(cls, str) else cls.__name__

        with self.db.lock:
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
            self.db.begin()
            newID = self.db[tableName].insert(dict(**kwargs))
            self.db.commit()
            ret = cls(db=self, app=self.app, id=newID, **kwargs)
        return ret

    def Upsert(self, obj):
        ret = None
        with self.db.lock:
            self.db.begin()
            ret = self.db[type(obj).__name__].upsert(dict(obj), ['id'])
            self.db.commit()
        return ret

    def Delete(self, obj):
        ret = None
        with self.db.lock:
            self.db.begin()
            ret = self.db[type(obj).__name__].delete(id=obj['id'])
            self.db.commit()
        return ret

    def Drop(self, cls, confirm=False):
        tableName = cls if isinstance(cls, str) else cls.__name__

        if confirm is False:
            raise Exception('You must pass confirm=True to Drop a table.')
        with self.db.lock:
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

    def Append(self, key, value):
        '''
        Usage:
            self.Append('items', item)

        Is equal to:
            items = self.Get('items', [])
            items.append(item)
            self.Set('items', items)

        :param key:
        :param value:
        :return:
        '''
        items = self.Get(key, [])
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
