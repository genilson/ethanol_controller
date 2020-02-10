#!/usr/bin/python
# -*- coding: utf-8 -*-

""" implements the following messages:

'MSG_GET_WMM_PARAMS',
'MSG_SET_WMM_PARAMS'

@author: Genilson Israel da silva
@organization: NETLAB/PGCC/UFJF
@copyright: genilson (c) 2019
@contact: genilsonisrael@gmail.com
@licence: GNU General Public License v2.0
(https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
@since: December, 2019
@status: in development

@requires: construct 2.5.2
"""

from construct import Embed, Array, Struct, Container, SLInt32, Array

from pox.ethanol.ssl_message.msg_core import msg_default, field_station,\
											 field_intf_name
from pox.ethanol.ssl_message.msg_common import MSG_TYPE, VERSION,\
											   send_and_receive_msg, len_of_string

################################
#     'MSG_GET_WMM_PARAMS'.    #
#     'MSG_SET_WMM_PARAMS'     #
################################

ac_params = Struct('ac_params',
                   SLInt32('aifs'),
				   SLInt32('cwmin'), #0..15 with cwmax >= cwmin.
				   					#actual cw used will be (2^n)-1
				   SLInt32('cwmax'),
				   SLInt32('txop_limit'), #in units of 32us
				   SLInt32('admission_control_mandatory'), # 0 or 1, maybe use Flag
				   )

# Message that embodies the 4 AC WMM parameters
msg_wmm_ac_params = Struct('msg_wmm_ac_params',
							Embed(msg_default),
							Embed(field_station),
							Embed(field_intf_name),
							SLInt32('ac'),
							Array(4, ac_params), #AC_BE, AC_BK, AC_VI, AC_VO
						  )

msg_wmm_single_ac_params = Struct('msg_wmm_single_ac_params',
                                  Embed(msg_default),
								  Embed(field_station),
								  Embed(field_intf_name),
								  SLInt32('ac'),
								  Array(1, ac_params),
                                  )

def get_wmm_params(server, id=0, ac=-1, intf_name=None, sta_ip=None, sta_port=0):
	"""Requests WMM params from a interface. Altough WMM is enabled per SSID,
	   WMM params are set per interface.
	
	This function requests aifs, cwmin, cwmax, txop limit and admission control
	mandatory values from a specific interface on the access point.
	
	Default values are negative, which are not valid parameters.

	@param server: tuple (ip, port_num)
	@param id: message id
	@param intf_name: name of the wireless interface
	@type intf_name: str
	@param sta_ip: ip address of the station that this message should be
				   relayed to, if sta_ip is different from None
	@type sta_ip: str
	@param sta_port: socket port number of the station
	@type sta_port: int

	@return: msg - received message, with control fields and payload
	@return: value - payload of the message, which are the wmm params
	"""

	entry = Container(
		    aifs=-1,
			cwmin=-1,
			cwmax=-1,
			txop_limit=-1,
			admission_control_mandatory=-1,
		)

	# IF no access category was provided, an array is integrated in the message
	# so parameters from all access categories are retrieved
	params = []
	if (ac == -1):	
		for i in xrange(0,4):
			params.append(entry)
	else:
		# If an acess category is provied, a single container is integrated in
		# the message, so the parameters of the specific access category are
		# retrieved
		params.append(entry)

    # Creates the message that will be sent to the access point
	msg_struct = Container(
		m_type=MSG_TYPE.MSG_GET_WMM_PARAMS,
		m_id=id,
		p_version_length=len_of_string(VERSION),
		p_version=VERSION,
		m_size=-1,
		sta_ip_size=len_of_string(sta_ip),
        sta_ip=sta_ip,
        sta_port=sta_port,
        intf_name_size=len_of_string(intf_name),
        intf_name=intf_name,
        ac=ac, # only useful if a single access category is being queried
        ac_params=params,
	)

	# If an access category was especified, a message with a single ac_params
	# structure is sent. Otherwise, a 4 sized array is sent instead.
	if (ac == -1):
		error, msg = send_and_receive_msg(server, msg_struct,
		                                  msg_wmm_ac_params.build,
		                                  msg_wmm_ac_params.parse)
	else:
		error, msg = send_and_receive_msg(server, msg_struct,
		                                  msg_wmm_single_ac_params.build,
		                                  msg_wmm_single_ac_params.parse)

	if not error:
		value = msg['ac_params'] if 'ac_params' in msg else None
	else:
		value = []

	return msg, value