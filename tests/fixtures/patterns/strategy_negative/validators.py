# Fixture: Negative Strategy pattern
# Polymorphic family exists but NO class composes the base —
# so this should NOT produce a Strategy finding.

class Validator:
    """Base validator."""
    def validate(self, value):
        raise NotImplementedError


class EmailValidator(Validator):
    def validate(self, value):
        return "@" in value


class PhoneValidator(Validator):
    def validate(self, value):
        return value.isdigit()


# No Context class composes Validator — missing the Strategy context half.
class UserForm:
    def submit(self):
        pass
