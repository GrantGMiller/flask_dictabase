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
        self.db.close()

    def FindAll(self, cls, **kwargs):

        reverse = kwargs.pop('_reverse', False)  # bool
        orderBy = kwargs.pop('_orderBy', None)  # str
        if reverse is True:
            if orderBy is not None:
                orderBy = '-' + orderBy
            else:
                orderBy = '-id'

        if orderBy is not None:
            for obj in self.db[cls.__name__].find(
                    order_by=[f'{orderBy}'],
                    **kwargs
            ):
                yield cls(db=self, **obj)
        else:
            for obj in self.db[cls.__name__].find(**kwargs):
                yield cls(db=self, **obj)

    def FindOne(self, cls, **kwargs):
        ret = self.db[cls.__name__].find_one(**kwargs)
        if ret:
            ret = cls(db=self, **ret)
            return ret
        else:
            return None

    def New(self, cls, **kwargs):
        ret = None
        with self.db.lock:
            self.db.begin()
            newID = self.db[cls.__name__].insert(dict(**kwargs))
            self.db.commit()
            ret = cls(db=self, id=newID, **kwargs)
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
        if confirm is False:
            raise Exception('You must pass confirm=True to Drop a table.')
        self.db.begin()
        ret = self.db[cls.__name__].drop()
        self.db.commit()
        return ret


class BaseTable(dict):
    def __init__(self, *a, **k):
        self.db = k.pop('db')
        super().__init__(*a, **k)

    def Commit(self):
        ret = self.db.Upsert(self)
        return ret

    def __setitem__(self, *a, **k):
        super().__setitem__(*a, **k)
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
