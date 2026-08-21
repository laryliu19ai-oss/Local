openResults("/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/psf")
selectResults("tran")
sig_list = outputs()
p = outfile("/tmp/all_outputs.txt" "w")
foreach(s sig_list
    fprintf(p "%s\n" s)
)
close(p)
exit()
