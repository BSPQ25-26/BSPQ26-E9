REST API Reference
==================

Wallabot exposes its functionality through four independent HTTP REST services.
This section documents every public endpoint, request/response schema, and error
contract — the equivalent of an RMI interface specification.

All services accept and return **JSON** (``Content-Type: application/json``).
Endpoints that require authentication expect a ``Bearer`` token in the
``Authorization`` header issued by the Auth Service.

.. toctree::
   :maxdepth: 2

   auth_api
   inventory_api
   transaction_api
   agentic_api
