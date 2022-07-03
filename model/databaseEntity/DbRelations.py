
class DbRelations:

    def setupRelations(self):
        Customer.invoices = relationship("Invoice", order_by=Invoice.id, back_populates="customer")
        Base.metadata.create_all(engine)
