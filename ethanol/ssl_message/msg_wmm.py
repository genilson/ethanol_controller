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
from pox.core import core

################################
#     'MSG_GET_WMM_PARAMS'.    #
#     'MSG_SET_WMM_PARAMS'     #
################################

log = core.getLogger()

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
	"""Requests WMM params from an interface. Although WMM is enabled per SSID,
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
		# If an access category is provided, a single container is integrated in
		# the message, so the parameters of the specific access category are
		# retrieved
		params.append(entry)

    # Creates the message that will be sent to the access point
	msg_struct = Container(
		m_type=MSG_TYPE.MSG_GET_WMM_PARAMS,
		m_id=id,
		p_version_length=len_of_string(VERSION),
		p_version=VERSION,
		m_size=0,
		sta_ip_size=len_of_string(sta_ip),
        sta_ip=sta_ip,
        sta_port=sta_port,
        intf_name_size=len_of_string(intf_name),
        intf_name=intf_name,
        ac=ac, # only useful if a single access category is being queried
        ac_params=params,
	)

	# If an access category was specified, a message with a single ac_params
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

def set_wmm_params(server, id=0, intf_name=None,
				   ac=-1, aifs=-1, cwmin=-1, cwmax=-1, txop_limit=-1,
				   admission_control_mandatory=-1, sta_ip=None, sta_port=0):
	
	"""Creates and sends a message to the AP containing WMM params for an AC
	(Access Category) on an interface.
	
	This function validates values for WMM params and sends a message to AP
	with those values. -1 is default and, because it's not a valid value for
	any of the parameters, it's used as a flag to indicate that no changes
	should be made for that specific parameter. An Access Category must be
	informed.

	Note: Here, cwMin and cmMax are in exponent form. The actual cw value used
	will be (2^n)-1 where n is the value given here.
	
	@param server: tuple (ip, port_num)
	@param id: message id
	@param intf_name: name of the wireless interface
	@type intf_name: str
	@param ac: Access Category to be modified
	@type ac: int
	@param aifs: Arbitration Inter-frame Spacing for the AC
	@type aifs: int
	@param cwmin: Minimum Contention Window, must be < than cwmax
	@type cwmin: int
	@param cwmax: Maximum Contention Window, must be > than cwmin
	@type cwmax: int
	@param txop_limit: Transmit Opportunity (in units of 32 microseconds)
	@type txop_limit: int
	@param admission_control_mandatory: whether or not admission control is
										mandatory
	@type admission_control_mandatory: int
	@param sta_ip: ip address of the station that this message should be
				   relayed to, if sta_ip is different from None
	@type sta_ip: str
	@param sta_port: socket port number of the station
	@type sta_port: int

	"""

	# Validate values before sending the message to avoid the extra overhead.
	# -1 is the default value and indicates that the parameters must not be
	# altered on destination.
	
	error_msg = []

	# A valid Access Category Index must be provided. No defaults here
	if ac < 0 or ac > 3:
		error_msg.append("ACI")

	# Except for the AC, the other parameters are optional. If at least one of
	# them isn't valid, nothing is done
	if (aifs != -1) and (aifs < 1 or aifs > 255):
		error_msg.append("aifs")

	if (cwmin != -1) and (cwmin < 0 or cwmin > 15 or cwmin > cwmax):
		error_msg.append("cwmin")

	if (cwmax != -1) and (cwmax < 0 or cwmax > 15 or cwmax < cwmin):
		error_msg.append("cwmax")

	if (txop_limit != -1) and (txop_limit < 0 or txop_limit > 0xffff):
		error_msg.append("txop_limit")

	if (admission_control_mandatory != -1) and (admission_control_mandatory
			not in [0,1]):
		error_msg.append("admission_control_mandatory")

	# Nothing to be changed
	if (aifs == cwmin == cwmax == txop_limit == admission_control_mandatory
	    == -1):
		error_msg.append("No change was requested.")

	if len(error_msg) != 0:
		log.error("Invalid value(s): %s." % ", ".join(error_msg));
		return

	entry = Container(
		    aifs=aifs,
			cwmin=cwmin,
			cwmax=cwmax,
			txop_limit=txop_limit,
			admission_control_mandatory=admission_control_mandatory,
		)

	# Message struct requires an array
	params = []
	params.append(entry)

	# Creates the message that will be sent to the access point
	msg_struct = Container(
		m_type=MSG_TYPE.MSG_SET_WMM_PARAMS,
		m_id=id,
		p_version_length=len_of_string(VERSION),
		p_version=VERSION,
		m_size=0,
		sta_ip_size=len_of_string(sta_ip),
        sta_ip=sta_ip,
        sta_port=sta_port,
        intf_name_size=len_of_string(intf_name),
        intf_name=intf_name,
        ac=ac,
        ac_params=params,
	)

	# Because validation is performed server-side, no response is expected 
	send_and_receive_msg(server, msg_struct, msg_wmm_single_ac_params.build,
		                 msg_wmm_single_ac_params.parse, only_send=True)