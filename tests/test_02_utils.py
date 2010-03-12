#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zlib
import base64
import gzip

from saml2 import utils, saml, samlp, md
from saml2.utils import do_attribute_statement, make_instance
from saml2.sigver import make_temp
from saml2.config import do_assertions
from saml2.saml import Attribute, NAME_FORMAT_URI, AttributeValue
from py.test import raises

SUCCESS_STATUS = """<?xml version=\'1.0\' encoding=\'UTF-8\'?>
<ns0:Status xmlns:ns0="urn:oasis:names:tc:SAML:2.0:protocol"><ns0:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" /></ns0:Status>"""

ERROR_STATUS = """<?xml version='1.0' encoding='UTF-8'?>
<ns0:Status xmlns:ns0="urn:oasis:names:tc:SAML:2.0:protocol"><ns0:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Responder"><ns0:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:UnknownPrincipal" /></ns0:StatusCode><ns0:StatusMessage>Error resolving principal</ns0:StatusMessage></ns0:Status>"""


def _eq(l1,l2):
    return set(l1) == set(l2)

def _oeq(l1,l2):
    if len(l1) != len(l2):
        print "Different number of items"
        return False
    for item in l1:
        if item not in l2:
            print "%s not in l2" % (item,)
            for ite in l2:
                print "\t%s" % (ite,)
            return False
    return True
    
def test_inflate_then_deflate():
    str = """Selma Lagerlöf (1858-1940) was born in Östra Emterwik, Värmland, 
    Sweden. She was brought up on Mårbacka, the family estate, which she did 
    not leave until 1881, when she went to a teachers' college at Stockholm"""
    
    interm = utils.deflate_and_base64_encode(str)
    bis = utils.decode_base64_and_inflate(interm)    
    assert bis == str
    
def test_status_success():
    stat = utils.args2dict(
            status_code=utils.args2dict(value=samlp.STATUS_SUCCESS))
    status = make_instance( samlp.Status, stat)
    status_text = "%s" % status
    assert status_text == SUCCESS_STATUS
    assert status.status_code.value == samlp.STATUS_SUCCESS
    
def test_success_status():
    stat = utils.success_status_factory()
    status = make_instance(samlp.Status, stat)
    status_text = "%s" % status
    assert status_text == SUCCESS_STATUS
    assert status.status_code.value == samlp.STATUS_SUCCESS

def test_error_status():
    stat = utils.args2dict(
        status_message=utils.args2dict("Error resolving principal"),
        status_code=utils.args2dict(
                        value=samlp.STATUS_RESPONDER,
                        status_code=utils.args2dict(
                            value=samlp.STATUS_UNKNOWN_PRINCIPAL)))
        
    status_text = "%s" % make_instance( samlp.Status, stat )
    print status_text
    assert status_text == ERROR_STATUS

def test_status_from_exception():
    e = utils.UnknownPrincipal("Error resolving principal")
    stat = utils.status_from_exception_factory(e)
    print stat
    status_text = "%s" % make_instance( samlp.Status, stat )
    print status_text
    assert status_text == ERROR_STATUS
    
def test_make_vals_str():
    kl = utils.make_vals("Jeter",md.GivenName, part=True)
    assert isinstance(kl, md.GivenName)
    assert kl.text == "Jeter"

def test_make_vals_int():
    kl = utils.make_vals(1024,md.KeySize, part=True)
    assert isinstance(kl, md.KeySize)
    assert kl.text == "1024"

def test_exception_make_vals_int_not_part():
    raises(TypeError, "utils.make_vals(1024,md.KeySize)")
    raises(TypeError, "utils.make_vals(1024,md.KeySize,md.EncryptionMethod())")
    raises(AttributeError, "utils.make_vals(1024,md.KeySize,prop='key_size')")
    
def test_make_vals_list_of_ints():
    em = md.EncryptionMethod()
    utils.make_vals([1024,2048], md.KeySize, em, "key_size")
    assert len(em.key_size) == 2    

def test_make_vals_list_of_strs():
    cp = md.ContactPerson()
    utils.make_vals(["Derek","Sanderson"], md.GivenName, cp, "given_name")
    assert len(cp.given_name) == 2
    assert _eq([i.text for i in cp.given_name],["Sanderson","Derek"])

def test_exception_make_vals_value_error():
    raises(ValueError, "utils.make_vals((1024,'xyz'), md.KeySize, part=True)")
    
def test_attribute():
    attr = utils.do_attributes({"surName":"Jeter"})
    
    assert len(attr) == 1
    inst = make_instance(saml.Attribute, attr[0])
    print inst
    assert inst.name == "surName"
    assert len(inst.attribute_value) == 1
    assert inst.attribute_value[0].text == "Jeter"
    
def test_attribute_statement():
    astat = do_attribute_statement({"surName":"Jeter",
                                        "givenName":"Derek"})
    print astat
    statement = make_instance(saml.AttributeStatement,astat)
    print statement
    assert statement.keyswv() == ["attribute"]
    assert len(statement.attribute) == 2
    attr0 = statement.attribute[0]
    assert _eq(attr0.keyswv(), ["name","attribute_value"])
    assert len(attr0.attribute_value) == 1
    attr1 = statement.attribute[1]
    assert _eq(attr1.keyswv(), ["name","attribute_value"])
    assert len(attr1.attribute_value) == 1
    if attr0.name == "givenName":
        assert attr0.attribute_value[0].text == "Derek"
        assert attr1.name == "surName"
        assert attr1.attribute_value[0].text == "Jeter"
    else:
        assert attr0.name == "surName"
        assert attr0.attribute_value[0].text == "Jeter"
        assert attr1.name == "givenName"
        assert attr1.attribute_value[0].text == "Derek"

def test_audience():
    aud_restr = make_instance( saml.AudienceRestriction, 
            utils.args2dict(
                    audience=utils.args2dict("urn:foo:bar")))
            
    assert aud_restr.keyswv() == ["audience"]
    assert aud_restr.audience.text == "urn:foo:bar"
    
def test_conditions():
    conds_dict = utils.args2dict(
                    not_before="2009-10-30T07:58:10.852Z",
                    not_on_or_after="2009-10-30T08:03:10.852Z", 
                    audience_restriction=utils.args2dict(
                        audience=utils.args2dict("urn:foo:bar")))
                    
    conditions = make_instance(saml.Conditions, conds_dict)
    assert _eq(conditions.keyswv(), ["not_before", "not_on_or_after",
                                "audience_restriction"])
    assert conditions.not_before == "2009-10-30T07:58:10.852Z" 
    assert conditions.not_on_or_after == "2009-10-30T08:03:10.852Z"
    assert conditions.audience_restriction[0].audience.text == "urn:foo:bar"
    
def test_value_1():
    #FriendlyName="givenName" Name="urn:oid:2.5.4.42" 
    # NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
    adict = utils.args2dict(name="urn:oid:2.5.4.42",
                                    name_format=NAME_FORMAT_URI)
    attribute = make_instance(saml.Attribute, adict)
    assert _eq(attribute.keyswv(),["name","name_format"])
    assert attribute.name == "urn:oid:2.5.4.42"
    assert attribute.name_format == saml.NAME_FORMAT_URI

def test_value_2():
    adict = utils.args2dict(name="urn:oid:2.5.4.42",
                                    name_format=NAME_FORMAT_URI,
                                    friendly_name="givenName")
    attribute = make_instance(saml.Attribute, adict)
    assert _eq(attribute.keyswv(),["name","name_format","friendly_name"])
    assert attribute.name == "urn:oid:2.5.4.42"
    assert attribute.name_format == NAME_FORMAT_URI
    assert attribute.friendly_name == "givenName"

def test_value_3():
    adict = utils.args2dict(attribute_value="Derek",
                                    name="urn:oid:2.5.4.42",
                                    name_format=NAME_FORMAT_URI,
                                    friendly_name="givenName")
    attribute = make_instance(saml.Attribute, adict)
    assert _eq(attribute.keyswv(),["name", "name_format",
                                    "friendly_name", "attribute_value"])
    assert attribute.name == "urn:oid:2.5.4.42"
    assert attribute.name_format == NAME_FORMAT_URI
    assert attribute.friendly_name == "givenName"
    assert len(attribute.attribute_value) == 1
    assert attribute.attribute_value[0].text == "Derek"

def test_value_4():
    adict = utils.args2dict(attribute_value="Derek",
                                    friendly_name="givenName")
    attribute = make_instance(saml.Attribute, adict)
    assert _eq(attribute.keyswv(),["friendly_name", "attribute_value"])
    assert attribute.friendly_name == "givenName"
    assert len(attribute.attribute_value) == 1
    assert attribute.attribute_value[0].text == "Derek"

def test_do_attribute_statement_0():
    astat = do_attribute_statement({"vo_attr":"foobar"})
    statement = make_instance(saml.AttributeStatement,astat)
    assert statement.keyswv() == ["attribute"]
    assert len(statement.attribute) == 1
    attr0 = statement.attribute[0]
    assert _eq(attr0.keyswv(), ["name","attribute_value"])
    assert attr0.name == "vo_attr"
    assert len(attr0.attribute_value) == 1
    assert attr0.attribute_value[0].text == "foobar"

def test_do_attribute_statement():
    astat = do_attribute_statement({"surName":"Jeter",
                                        "givenName":["Derek","Sanderson"]})
    statement = make_instance(saml.AttributeStatement, astat)
    assert statement.keyswv() == ["attribute"]
    assert len(statement.attribute) == 2
    attr0 = statement.attribute[0]
    assert _eq(attr0.keyswv(), ["name","attribute_value"])
    attr1 = statement.attribute[1]
    assert _eq(attr1.keyswv(), ["name","attribute_value"])
    if attr0.name == "givenName":
        assert len(attr0.attribute_value) == 2
        assert _eq([av.text for av in attr0.attribute_value],
                    ["Derek","Sanderson"])
        assert attr1.name == "surName"
        assert attr1.attribute_value[0].text == "Jeter"
        assert len(attr1.attribute_value) == 1
    else:
        assert attr0.name == "surName"
        assert attr0.attribute_value[0].text == "Jeter"
        assert len(attr0.attribute_value) == 1
        assert attr1.name == "givenName"
        assert len(attr1.attribute_value) == 2
        assert _eq([av.text for av in attr1.attribute_value],
                    ["Derek","Sanderson"])
    
def test_do_attribute_statement_multi():
    astat = do_attribute_statement(
                {( "urn:oid:1.3.6.1.4.1.5923.1.1.1.7",
                    "urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
                    "eduPersonEntitlement"):"Jeter"})
    statement = make_instance(saml.AttributeStatement,astat)
    assert statement.keyswv() == ["attribute"]
    assert len(statement.attribute)
    assert _eq(statement.attribute[0].keyswv(),
                ["name","name_format","friendly_name","attribute_value"])
    attribute = statement.attribute[0]
    assert attribute.name == "urn:oid:1.3.6.1.4.1.5923.1.1.1.7"
    assert attribute.name_format == (
                "urn:oasis:names:tc:SAML:2.0:attrname-format:uri")
    assert attribute.friendly_name == "eduPersonEntitlement"

def test_subject():
    adict = utils.args2dict("_aaa", name_id=saml.NAMEID_FORMAT_TRANSIENT)
    subject = make_instance(saml.Subject, adict)
    assert _eq(subject.keyswv(),["text", "name_id"])
    assert subject.text == "_aaa"
    assert subject.name_id.text == saml.NAMEID_FORMAT_TRANSIENT
    


AVA = [
    {
        "surName": ["Jeter"],
        "givenName": ["Derek"],
    },
    {
        "surName": ["Howard"],
        "givenName": ["Ryan"],
    },
    {
        "surName": ["Suzuki"],
        "givenName": ["Ischiro"],
    },
    {
        "surName": ["Hedberg"],
        "givenName": ["Roland"],
    },
]    

def test_filter_attribute_value_assertions_0():
    assertion = {
        "default": {
            "attribute_restrictions": {
                "surName": [".*berg"],
            }
        }
    }
    
    ass = do_assertions(assertion)
    print ass
    
    ava = utils.filter_attribute_value_assertions(AVA[3], 
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert ava.keys() == ["surName"]
    assert ava["surName"] == ["Hedberg"]

def test_filter_attribute_value_assertions_1():
    assertion = {
        "default": {
            "attribute_restrictions": {
                "surName": None,
                "givenName": [".*er.*"],
            }
        }
    }
    
    ass = do_assertions(assertion)
    print ass
    
    ava = utils.filter_attribute_value_assertions(AVA[0], 
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert _eq(ava.keys(), ["givenName","surName"])
    assert ava["surName"] == ["Jeter"]
    assert ava["givenName"] == ["Derek"]

    ava = utils.filter_attribute_value_assertions(AVA[1],
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert _eq(ava.keys(), ["surName"])
    assert ava["surName"] == ["Howard"]
    
    
def test_filter_attribute_value_assertions_2():
    assertion = {
        "default": {
            "attribute_restrictions": {
                "givenName": ["^R.*"],
            }
        }
    }
    
    ass = do_assertions(assertion)
    print ass

    ava = utils.filter_attribute_value_assertions(AVA[0], 
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert _eq(ava.keys(), [])
    
    ava = utils.filter_attribute_value_assertions(AVA[1], 
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert _eq(ava.keys(), ["givenName"])
    assert ava["givenName"] == ["Ryan"]

    ava = utils.filter_attribute_value_assertions(AVA[3], 
                ass["default"]["attribute_restrictions"])
    
    print ava
    assert _eq(ava.keys(), ["givenName"])
    assert ava["givenName"] == ["Roland"]

def test_parse_attribute_map():
    (forward, backward) = utils.parse_attribute_map(["attribute.map"])
    
    assert _eq(forward.keys(), backward.values())
    assert _eq(forward.values(), backward.keys())
    print forward.keys()
    assert _oeq(forward.keys(), [
            ('urn:oid:1.3.6.1.4.1.5923.1.1.1.7', NAME_FORMAT_URI), 
            ('urn:oid:0.9.2342.19200300.100.1.1', NAME_FORMAT_URI), 
            ('urn:oid:1.3.6.1.4.1.5923.1.1.1.1', NAME_FORMAT_URI), 
            ('urn:oid:2.5.4.42', NAME_FORMAT_URI),
            ('urn:oid:2.5.4.4', NAME_FORMAT_URI),
            ('urn:oid:0.9.2342.19200300.100.1.3', NAME_FORMAT_URI), 
            ('urn:oid:2.5.4.12', NAME_FORMAT_URI)])
    assert _eq(forward.keys(), [
            ('urn:oid:1.3.6.1.4.1.5923.1.1.1.7', NAME_FORMAT_URI), 
            ('urn:oid:0.9.2342.19200300.100.1.1', NAME_FORMAT_URI), 
            ('urn:oid:1.3.6.1.4.1.5923.1.1.1.1', NAME_FORMAT_URI), 
            ('urn:oid:2.5.4.42', NAME_FORMAT_URI),
            ('urn:oid:2.5.4.4', NAME_FORMAT_URI),
            ('urn:oid:0.9.2342.19200300.100.1.3', NAME_FORMAT_URI), 
            ('urn:oid:2.5.4.12', NAME_FORMAT_URI)])
    assert _eq(backward.keys(),["surName","givenName","title","uid","mail",
                                    "eduPersonAffiliation",
                                    "eduPersonEntitlement"])
                                    

def test_identity_attribute_0():
    (forward, backward) = utils.parse_attribute_map(["attribute.map"])
    a = Attribute(name="urn:oid:2.5.4.4", name_format=NAME_FORMAT_URI,
                    friendly_name="surName")
    
    assert utils.identity_attribute("name",a,forward) == "urn:oid:2.5.4.4"
    assert utils.identity_attribute("friendly",a,forward) == "surName"
                                    
def test_identity_attribute_1():
    (forward, backward) = utils.parse_attribute_map(["attribute.map"])
    a = Attribute(name="urn:oid:2.5.4.4", name_format=NAME_FORMAT_URI)
    
    assert utils.identity_attribute("name",a,forward) == "urn:oid:2.5.4.4"
    assert utils.identity_attribute("friendly",a,forward) == "surName"

def test_identity_attribute_2():
    (forward, backward) = utils.parse_attribute_map(["attribute.map"])
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI)
    
    assert utils.identity_attribute("name",a,forward) == "urn:oid:2.5.4.5"
    # if there would be a map it would be serialNumber
    assert utils.identity_attribute("friendly",a,forward) == "urn:oid:2.5.4.5"

def test_identity_attribute_3():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI)
    
    assert utils.identity_attribute("name",a) == "urn:oid:2.5.4.5"
    # if there would be a map it would be serialNumber
    assert utils.identity_attribute("friendly",a) == "urn:oid:2.5.4.5"

def test_identity_attribute_4():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber")
    
    assert utils.identity_attribute("name",a) == "urn:oid:2.5.4.5"
    # if there would be a map it would be serialNumber
    assert utils.identity_attribute("friendly",a) == "serialNumber"
    
def test_combine_0():
    r = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber")    
    o = Attribute(name="urn:oid:2.5.4.4", name_format=NAME_FORMAT_URI,
                    friendly_name="surName")

    comb = utils._combine([r],[o])
    print comb
    assert _eq(comb.keys(), [('urn:oid:2.5.4.5', 'serialNumber'), 
                                ('urn:oid:2.5.4.4', 'surName')])
    assert comb[('urn:oid:2.5.4.5', 'serialNumber')] == ([], [])
    assert comb[('urn:oid:2.5.4.4', 'surName')] == ([], [])
    

def test_filter_on_attributes_0():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber")    
    
    required = [a]
    ava = { "serialNumber": ["12345"]}
    
    ava = utils.filter_on_attributes(ava, required)
    assert ava.keys() == ["serialNumber"]
    assert ava["serialNumber"] == ["12345"]

def test_filter_on_attributes_1():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber")    
    
    required = [a]
    ava = { "serialNumber": ["12345"], "givenName":["Lars"]}
    
    ava = utils.filter_on_attributes(ava, required)
    assert ava.keys() == ["serialNumber"]
    assert ava["serialNumber"] == ["12345"]

def test_filter_values_req_2():
    a1 = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber")    
    a2 = Attribute(name="urn:oid:2.5.4.4", name_format=NAME_FORMAT_URI,
                    friendly_name="surName")
    
    required = [a1,a2]
    ava = { "serialNumber": ["12345"], "givenName":["Lars"]}
    
    raises(utils.MissingValue, utils.filter_on_attributes, ava, required)

def test_filter_values_req_3():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="12345")])    
    
    required = [a]
    ava = { "serialNumber": ["12345"]}
    
    ava = utils.filter_on_attributes(ava, required)
    assert ava.keys() == ["serialNumber"]
    assert ava["serialNumber"] == ["12345"]

def test_filter_values_req_4():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="54321")])    
    
    required = [a]
    ava = { "serialNumber": ["12345"]}
    
    raises(utils.MissingValue, utils.filter_on_attributes, ava, required)

def test_filter_values_req_5():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="12345")])    
    
    required = [a]
    ava = { "serialNumber": ["12345", "54321"]}
    
    ava = utils.filter_on_attributes(ava, required)
    assert ava.keys() == ["serialNumber"]
    assert ava["serialNumber"] == ["12345"]

def test_filter_values_req_6():
    a = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="54321")])    
    
    required = [a]
    ava = { "serialNumber": ["12345", "54321"]}
    
    ava = utils.filter_on_attributes(ava, required)
    assert ava.keys() == ["serialNumber"]
    assert ava["serialNumber"] == ["54321"]

def test_filter_values_req_opt_0():
    r = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="54321")])    
    o = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="12345")])    
    
    ava = { "serialNumber": ["12345", "54321"]}
    
    ava = utils.filter_on_attributes(ava, [r], [o])
    assert ava.keys() == ["serialNumber"]
    assert _eq(ava["serialNumber"], ["12345","54321"])

def test_filter_values_req_opt_1():
    r = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="54321")])    
    o = Attribute(name="urn:oid:2.5.4.5", name_format=NAME_FORMAT_URI,
                    friendly_name="serialNumber", attribute_value=[
                        AttributeValue(text="12345"),
                        AttributeValue(text="abcd0")])    
    
    ava = { "serialNumber": ["12345", "54321"]}
    
    ava = utils.filter_on_attributes(ava, [r], [o])
    assert ava.keys() == ["serialNumber"]
    assert _eq(ava["serialNumber"], ["12345","54321"])

def _givenName(a):
    assert a["name"] == "urn:oid:2.5.4.42"
    assert a["friendly_name"] == "givenName"
    assert len(a["attribute_value"]) == 1
    assert a["attribute_value"] == [{"text":"Derek"}]

def _surName(a):
    assert a["name"] == "urn:oid:2.5.4.4"
    assert a["friendly_name"] == "surName"
    assert len(a["attribute_value"]) == 1
    assert a["attribute_value"] == [{"text":"Jeter"}]

def test_ava_to_attributes():
    (forward, backward) = utils.parse_attribute_map(["attribute.map"])
    attrs = utils.ava_to_attributes(AVA[0], backward)
    
    assert len(attrs) == 2
    a = attrs[0]
    if a["name"] == "urn:oid:2.5.4.42":
        _givenName(a)
        _surName(attrs[1])
    elif a["name"] == "urn:oid:2.5.4.4":
        _surName(a)
        _givenName(attrs[1])
    else:
        print a
        assert False
        
def test_nameformat_email():
    assert utils.valid_email("foo@example.com")
    assert utils.valid_email("a@b.com")
    assert utils.valid_email("a@b.se")
    assert utils.valid_email("john@doe@johndoe.com") == False
    
def test_args2dict():
    n = utils.args2dict("foo", name_qualifier="urn:mace:example.com:nq")
    assert _eq(n.keys(), ["text","name_qualifier"])
    assert n["text"] == "foo"
    assert n["name_qualifier"] == "urn:mace:example.com:nq"
        
def test_attribute():
    a = utils.args2dict(friendly_name="eduPersonScopedAffiliation",    
        name="urn:oid:1.3.6.1.4.1.5923.1.1.1.9",
        name_format="urn:oasis:names:tc:SAML:2.0:attrname-format:uri")
        
    assert _eq(a.keys(), ["friendly_name","name", "name_format"])

    a = utils.args2dict(friendly_name="eduPersonScopedAffiliation",    
        name="urn:oid:1.3.6.1.4.1.5923.1.1.1.9",
        name_format="urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
        attribute_value=utils.args2dict("member@example.com"))
        
    assert _eq(a.keys(), ["friendly_name","name", "name_format",
                            "attribute_value"])
                            
def test_attribute_statement():
    a = utils.args2dict(
                attribute=[
                    utils.args2dict(attribute_value="Derek", 
                                        friendly_name="givenName"),
                    utils.args2dict(attribute_value="Jeter", 
                                        friendly_name="surName"),
                ])
    assert a.keys() == ["attribute"]
    assert len(a["attribute"]) == 2
    
def test_subject_confirmation_data():
    s = utils.args2dict(
                in_response_to="_12345678", 
                not_before="2010-02-11T07:30:00Z",
                not_on_or_after="2010-02-11T07:35:00Z",
                recipient="http://example.com/sp/",
                address="192.168.0.10")
                
    assert _eq(s.keys(),["in_response_to","not_before","not_on_or_after",
                        "recipient", "address"])
    
def test_subject_confirmation():
    s = utils.args2dict(
                    method="urn:oasis:names:tc:SAML:2.0:profiles:SSO:browser",
                    base_id="1234",
                    name_id="abcd",
                    subject_confirmation_data=utils.args2dict(
                            in_response_to="_1234567890",
                            recipient="http://example.com/sp/"))

    assert _eq(s.keys(),
                ["method","base_id","name_id","subject_confirmation_data"])
    assert s["method"] == "urn:oasis:names:tc:SAML:2.0:profiles:SSO:browser"
    

def test_authn_context_class_ref():
    a = utils.args2dict(
            "urn:oasis:names:tc:SAML:2.0:ac:classes:unspecified")
    assert a.keys() == ["text"]
    assert a["text"] == "urn:oasis:names:tc:SAML:2.0:ac:classes:unspecified"
            
def test_authn_context():
    accr = utils.args2dict(
            "urn:oasis:names:tc:SAML:2.0:ac:classes:unspecified")
    a = utils.args2dict(authn_context_class_ref=accr)

    assert a.keys() == ["authn_context_class_ref"]
    
def test_authn_statement():
    accr = utils.args2dict(
            "urn:oasis:names:tc:SAML:2.0:ac:classes:unspecified")
    ac = utils.args2dict(authn_context_class_ref=accr)
    a = utils.args2dict(
                        authn_instant="2010-03-10T12:33:00Z",
                        session_index="_12345",
                        session_not_on_or_after="2010-03-11T12:00:00Z",
                        authn_context=ac
                        )