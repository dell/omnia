import ipaddress
import calculate_ip_details


def correlation_bmc_to_admin(bmc_ip, admin_ip_subnet, netmask_bits):
    """
       Calculates the correlated admin ip
       Parameters:
         bmc_ip: bmc-ip that needs to be used to form correlated admin ip
         admin_ip_subnet: network bits to be used for correlated admin ip
         netmask_bits: netmask bits of admin and bmc ip
       Returns:
         correlated admin ip
    """
    binary_admin_ip = calculate_ip_details.calculate_binary_ip(admin_ip_subnet)
    binary_bmc_ip = calculate_ip_details.calculate_binary_ip(bmc_ip)
    first_x_bits = calculate_ip_details.calculate_first_x_bits(binary_admin_ip, netmask_bits)
    last_y_bits = calculate_ip_details.calculate_last_y_bits(binary_bmc_ip, netmask_bits)
    final_admin_ip_binary = first_x_bits + last_y_bits
    int_final_admin_ip = int(final_admin_ip_binary, 2)
    final_admin_ip = ipaddress.IPv4Address(int_final_admin_ip)
    return final_admin_ip