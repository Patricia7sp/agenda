SUB = {
    "endpoint": "https://push.example.com/sub/abc",
    "keys": {"p256dh": "chave-publica-fake", "auth": "auth-fake"},
}


def test_subscription_exige_autenticacao(client):
    assert client.post("/api/v1/push/subscriptions", json=SUB).status_code == 401


def test_upsert_por_endpoint_nao_duplica(client, login):
    headers = login("push@exemplo.com")

    r1 = client.post("/api/v1/push/subscriptions", headers=headers, json=SUB)
    assert r1.status_code == 201

    atualizada = {**SUB, "keys": {"p256dh": "nova-chave", "auth": "novo-auth"}}
    r2 = client.post("/api/v1/push/subscriptions", headers=headers, json=atualizada)
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]

    listadas = client.get("/api/v1/push/subscriptions", headers=headers).json()
    assert len(listadas) == 1


def test_remocao_de_subscription(client, login):
    headers = login("remove@exemplo.com")
    client.post("/api/v1/push/subscriptions", headers=headers, json=SUB)

    r = client.request(
        "DELETE", "/api/v1/push/subscriptions", headers=headers, json={"endpoint": SUB["endpoint"]}
    )
    assert r.status_code == 204
    assert client.get("/api/v1/push/subscriptions", headers=headers).json() == []


def test_usuarios_nao_veem_subscriptions_um_do_outro(client, login):
    ana = login("ana@exemplo.com")
    bob = login("bob@exemplo.com")

    client.post("/api/v1/push/subscriptions", headers=ana, json=SUB)
    outra = {**SUB, "endpoint": "https://push.example.com/sub/xyz"}
    client.post("/api/v1/push/subscriptions", headers=bob, json=outra)

    da_ana = client.get("/api/v1/push/subscriptions", headers=ana).json()
    do_bob = client.get("/api/v1/push/subscriptions", headers=bob).json()

    assert [s["endpoint"] for s in da_ana] == [SUB["endpoint"]]
    assert [s["endpoint"] for s in do_bob] == [outra["endpoint"]]

    # Bob não consegue remover a subscription da Ana.
    client.request(
        "DELETE", "/api/v1/push/subscriptions", headers=bob, json={"endpoint": SUB["endpoint"]}
    )
    assert len(client.get("/api/v1/push/subscriptions", headers=ana).json()) == 1


def test_vapid_public_key(client):
    r = client.get("/api/v1/push/vapid-public-key")
    if r.status_code == 503:
        assert r.json()["code"] == "vapid_missing"
    else:
        assert r.status_code == 200
        assert r.json()["public_key"]
