// -*- c++ -*-
/*
 * Copyright 2012, 2013 The GalSim developers:
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 *
 * GalSim is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * GalSim is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GalSim.  If not, see <http://www.gnu.org/licenses/>
 */
#include "boost/python.hpp"
#include "boost/python/stl_iterator.hpp"

#include "SBConvolve.h"

namespace bp = boost::python;

namespace galsim {

    struct PySBConvolve 
    {

        // This will be wrapped as a Python constructor; it accepts an arbitrary Python iterable.
        static SBConvolve * construct(bp::object const & iterable, bool real_space) {
            bp::stl_input_iterator<SBProfile> begin(iterable), end;
            std::list<SBProfile> plist(begin, end);
            return new SBConvolve(plist, real_space);
        }

        static void wrap() {
            bp::class_< SBConvolve, bp::bases<SBProfile> >("SBConvolve", bp::no_init)
                // bp tries the overloads in reverse order, so we wrap the most general one first
                // to ensure we try it last
                .def("__init__", 
                     bp::make_constructor(&construct, bp::default_call_policies(), 
                                          (bp::arg("slist"), bp::arg("real_space")=false)
                     ))
                .def(bp::init<const SBProfile &, const SBProfile &, bool>(
                        (bp::args("s1", "s2"), bp::arg("real_space")=false)
                ))
                .def(bp::init<const SBProfile &, const SBProfile &, const SBProfile &, bool>(
                        (bp::args("s1", "s2", "s3"), bp::arg("real_space")=false)
                ))
                .def(bp::init<const SBConvolve &>())
                ;
        }

    };

    void pyExportSBConvolve() 
    {
        PySBConvolve::wrap();
    }

} // namespace galsim
