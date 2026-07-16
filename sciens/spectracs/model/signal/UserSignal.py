from sciens.spectracs.model.databaseEntity.DbEntityChangedSignal import DbEntityChangedSignal


class UserSignal(DbEntityChangedSignal):
    """Carries a plain user DTO (dict) + a DbEntityCrudOperation so the user list refreshes
    after a create/update/delete. Distinct from the parameterless userSessionSignal, which is
    about login state, not the user list."""
    pass
